import requests
import time
import json
from kafka import KafkaProducer
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Prometheus metrics
FLIGHTS_FETCHED = Counter("flights_fetched_total", "Total flights fetched from OpenSky API")
FLIGHTS_SENT = Counter("flights_sent_total", "Total flights sent to Kafka")
API_ERRORS = Counter("api_errors_total", "Total API errors", ["error_type"])
FETCH_DURATION = Histogram("fetch_duration_seconds", "Time spent fetching flight data")
KAFKA_SEND_ERRORS = Counter("kafka_send_errors_total", "Total errors sending to Kafka")
CURRENT_PROCESSING_LAG = Gauge("processing_lag_seconds", "Time between data fetch and processing")
PROCESSED_FLIGHTS_PER_BATCH = Gauge("flights_per_batch", "Number of flights processed per batch")

# Start Prometheus metrics server on port 8000
try:
    start_http_server(8000)
    print(" Prometheus metrics server started on http://localhost:8000/metrics")
except OSError as e:
    print(f"  Could not start metrics server on port 8000: {e}")

TOPIC = "realtime-flights"

INDIA_BOUNDS = (6.0, 38.0, 68.0, 97.0)


def fetch_flight_data():
    url = "https://opensky-network.org/api/states/all"
    response = None  # Initialize to avoid unbound error
    start_time = time.time()

    try:
        print(" Fetching data from OpenSky API...")
        response = requests.get(url, timeout=15)

        fetch_duration = time.time() - start_time
        FETCH_DURATION.observe(fetch_duration)

        print(f" Response status: {response.status_code}")

        if response.status_code != 200:
            print(f" API Error: Status {response.status_code}")
            API_ERRORS.labels(error_type="http_error").inc()
            return []

        if not response.text.strip():
            print(" Empty response from API")
            API_ERRORS.labels(error_type="empty_response").inc()
            return []

        data = response.json()
        states = data.get("states", [])

        if not states:
            print(" No flight data available")
            return []

        print(f"Total flights worldwide: {len(states)}")
        FLIGHTS_FETCHED.inc(len(states))

        filtered = []
        for s in states:
            if len(s) < 10:  # Ensure we have enough fields
                continue

            lat, lon = s[6], s[5]
            if lat and lon and INDIA_BOUNDS[0] <= lat <= INDIA_BOUNDS[1] and INDIA_BOUNDS[2] <= lon <= INDIA_BOUNDS[3]:
                filtered.append(
                    {
                        "icao24": s[0],
                        "callsign": s[1].strip() if s[1] else None,
                        "origin_country": s[2],
                        "time_position": s[3],
                        "longitude": s[5],
                        "latitude": s[6],
                        "baro_altitude": s[7],
                        "velocity": s[9],
                    }
                )

        print(f"🇮🇳 Flights over India: {len(filtered)}")
        PROCESSED_FLIGHTS_PER_BATCH.set(len(filtered))
        return filtered

    except requests.exceptions.Timeout:
        print(" Request timeout - API might be slow")
        API_ERRORS.labels(error_type="timeout").inc()
        return []
    except requests.exceptions.RequestException as e:
        print(f" Network error: {e}")
        API_ERRORS.labels(error_type="network").inc()
        return []
    except json.JSONDecodeError as e:
        print(f" JSON parsing error: {e}")
        if response:
            print(f"Response content: {response.text[:200]}...")
        API_ERRORS.labels(error_type="json_decode").inc()
        return []
    except Exception as e:
        print(f" Unexpected error: {e}")
        API_ERRORS.labels(error_type="unknown").inc()
        return []
    finally:
        # Track processing lag
        if "start_time" in locals():
            lag = time.time() - start_time
            CURRENT_PROCESSING_LAG.set(lag)


def stream_flights():
    """Continuously fetch flights and send to Kafka"""
    # Create Kafka producer inside the function (only needed when streaming)
    producer = KafkaProducer(
        bootstrap_servers="localhost:9092", value_serializer=lambda x: json.dumps(x).encode("utf-8")
    )

    while True:
        try:
            flights = fetch_flight_data()

            if flights:
                print(f"Fetched {len(flights)} flights")
                for flight in flights:
                    try:
                        producer.send(TOPIC, value=flight)
                        FLIGHTS_SENT.inc()
                    except Exception as e:
                        print(f" Failed to send flight {flight.get('icao24')}: {e}")
                        KAFKA_SEND_ERRORS.inc()
                print(f" Successfully sent {len(flights)} flights to Kafka")
            else:
                print("  No flights to send this round")

            print(" Waiting 20 seconds before next fetch...")
            time.sleep(20)
            print("=" * 50)

        except Exception as e:
            print(f" Stream error: {e}")
            KAFKA_SEND_ERRORS.inc()
            print("⏳ Waiting 20 seconds before retry...")
            time.sleep(20)


if __name__ == "__main__":
    stream_flights()
