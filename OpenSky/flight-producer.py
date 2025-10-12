import requests
import time
import json
from kafka import KafkaProducer

producer= KafkaProducer(
    bootstrap_servers= 'localhost:9092',
    value_serializer= lambda x: json.dumps(x).encode('utf-8')
)

TOPIC = 'realtime-flights'

INDIA_BOUNDS= (6.0,38.0,68.0,97.0)

def fetch_flight_data():
    url = "https://opensky-network.org/api/states/all"
    try:
        print("🔄 Fetching data from OpenSky API...")
        response = requests.get(url, timeout=15)
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API Error: Status {response.status_code}")
            return []
        
        if not response.text.strip():
            print("❌ Empty response from API")
            return []
            
        data = response.json()
        states = data.get('states', [])
        
        if not states:
            print("⚠️  No flight data available")
            return []
            
        print(f"📊 Total flights worldwide: {len(states)}")
        
        filtered = []
        for s in states:
            if len(s) < 10:  # Ensure we have enough fields
                continue
                
            lat, lon = s[6], s[5]
            if lat and lon and INDIA_BOUNDS[0] <= lat <= INDIA_BOUNDS[1] and INDIA_BOUNDS[2] <= lon <= INDIA_BOUNDS[3]:
                filtered.append({
                    "icao24": s[0],
                    "callsign": s[1].strip() if s[1] else None,
                    "origin_country": s[2],
                    "time_position": s[3],
                    "longitude": s[5],
                    "latitude": s[6],
                    "baro_altitude": s[7],
                    "velocity": s[9],
                })
        
        print(f"🇮🇳 Flights over India: {len(filtered)}")
        return filtered
        
    except requests.exceptions.Timeout:
        print("⏰ Request timeout - API might be slow")
        return []
    except requests.exceptions.RequestException as e:
        print(f"🌐 Network error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"📝 JSON parsing error: {e}")
        print(f"Response content: {response.text[:200]}...")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

def stream_flights():
    while True:
        try:
            flights = fetch_flight_data()
            
            if flights:
                print(f"✅ Fetched {len(flights)} flights")
                for flight in flights:
                    producer.send(TOPIC, value=flight)
                    print(f"📡 Sent flight: {flight.get('callsign', 'Unknown')}")
                print(f"🎯 Successfully sent {len(flights)} flights to Kafka")
            else:
                print("⚠️  No flights to send this round")
            
            print("⏳ Waiting 10 seconds before next fetch...")
            time.sleep(20)
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Stream error: {e}")
            print("⏳ Waiting 10 seconds before retry...")
            time.sleep(20)

if __name__ == "__main__":
    stream_flights()
    