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
    response = requests.get(url, timeout=10)
    data = response.json()
    states= data.get('states', [])
    filtered =[]
    
    for s in states:
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
    return filtered

def stream_flights():
    while True:
        try:
            flights= fetch_flight_data()
            print(f"Fetched {len(flights)} flights")
            for flight in flights:
                producer.send(TOPIC, value=flight)
                print(f"Sent flight: {flight['callsign']}")
            time.sleep(5)
            print("--------------------------------")
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    stream_flights()
    