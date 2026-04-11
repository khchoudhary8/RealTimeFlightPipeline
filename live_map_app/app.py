import os
import json
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiokafka import AIOKafkaConsumer

app = FastAPI()
templates = Jinja2Templates(directory="templates")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
TOPIC = "realtime-flights"

# Jamshedpur: 22.8046° N, 86.2029° E
# Max 500km Bounding Box (+/- ~4.5 degrees)
JAMSHEDPUR_BOUNDS = {
    "min_lat": 18.30,
    "max_lat": 27.30,
    "min_lon": 81.70,
    "max_lon": 90.70
}

def is_in_jamshedpur(lat, lon):
    if not lat or not lon:
        return False
    return (JAMSHEDPUR_BOUNDS["min_lat"] <= lat <= JAMSHEDPUR_BOUNDS["max_lat"]) and \
           (JAMSHEDPUR_BOUNDS["min_lon"] <= lon <= JAMSHEDPUR_BOUNDS["max_lon"])

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Initialize Kafka Consumer
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="live-map-websockets",
        auto_offset_reset="latest" # Only care about right now
    )
    
    try:
        await consumer.start()
        print("✅ Kafka Consumer started for WebSockets.")
        
        async for msg in consumer:
            flight = msg.value
            
            # Send all India-wide flights to the browser
            # Frontend will handle the radius filtering for Jamshedpur
            try:
                await websocket.send_json(flight)
            except Exception as e:
                print(f"Client disconnected: {e}")
                break
                    
    except Exception as e:
        print(f"❌ WebSocket/Kafka Error: {e}")
    finally:
        await consumer.stop()
        print("Kafka Consumer stopped.")
