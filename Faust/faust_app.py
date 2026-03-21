from typing import List
import faust
import os
import boto3
from dotenv import load_dotenv
import json
from datetime import datetime
import asyncio
load_dotenv()

app= faust.App(
    "flight-stream-processor",
    broker="kafka://localhost:9092",
    value_serializer="json",

)

class Flight (faust.Record, serializer="json"):  # type: ignore
    icao24: str
    callsign: str
    origin_country: str
    time_position:int
    longitude:float
    latitude:float
    baro_altitude:float
    velocity:float
    
topic = app.topic('realtime-flights', value_type=Flight)

s3= boto3.client('s3', 
                 region_name='ap-south-1',
                 aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                 aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
BUCKET_NAME='realtimeflightstreamingbuckett'

@app.agent(topic)
async def process_flight_data(flights: faust.StreamT):
    buffer: List[Flight] = []
    batch_interval = 10  # seconds

    async for flight in flights:
        buffer.append(flight)

        if len(buffer) == 1:
            # Start a timer on first element
            await asyncio.sleep(batch_interval)
            
            try:
                timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H%M%S')
                key = f"bronze/{timestamp}_batch.json"
                flight_dicts = [f.asdict() for f in buffer]
                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=key,
                    Body=json.dumps(flight_dicts).encode('utf-8')
                )
                print(f"Batch of {len(buffer)} flights saved to S3: {key}")
            except Exception as e:
                print(f"Error saving batch to S3: {e}")
            finally:
                buffer.clear()