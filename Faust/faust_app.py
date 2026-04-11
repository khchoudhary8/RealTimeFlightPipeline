import faust
import os
import boto3
from dotenv import load_dotenv
import json
from datetime import datetime
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
    # .take(count, within) collects 'count' events OR waits 'within' seconds
    async for batch in flights.take(200, within=10):
        if not batch:
            continue
            
        try:
            timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H%M%S')
            key = f"bronze/raw_flights/{timestamp}_batch.json"
            
            # Converts records to dicts for JSON serialization
            flight_dicts = [f.to_representation() for f in batch]
            
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=key,
                Body=json.dumps(flight_dicts).encode('utf-8')
            )
            print(f"📦 Batch of {len(batch)} flights saved to S3: {key}")
        except Exception as e:
            print(f"❌ Error saving batch to S3: {e}")