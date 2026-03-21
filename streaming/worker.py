import faust
import boto3
import json
import asyncio
from datetime import datetime
from config.settings import settings

# Initialize Faust App
app = faust.App(
    'flight-stream-worker',
    broker=f'kafka://{settings.KAFKA_BOOTSTRAP_SERVERS}',
    topic_partitions=1,
)

# Define the Topic
flight_topic = app.topic(settings.KAFKA_TOPIC_RAW, value_serializer='json')

# Initialize S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

# Buffer settings (simple in-memory buffer for 'baby steps')
# In a real heavy production, we'd use Faust Tables or external state, 
# but for "Raw Dump", a local buffer before flush is common.
BUFFER = []
BUFFER_SIZE = 10
LAST_FLUSH_TIME = datetime.now()

async def upload_to_s3(data_batch):
    """
    Uploads a batch of flights to S3 as a single JSON line file (NDJSON)
    """
    if not data_batch:
        return

    try:
        # Create a unique filename based on time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"bronze/raw_flights/{datetime.now().strftime('%Y-%m-%d')}/{timestamp}.json"
        
        # Convert list of dicts to NDJSON (Newline Delimited JSON)
        body = "\n".join([json.dumps(record) for record in data_batch])
        
        # Run S3 upload in a separate thread to avoid blocking the stream loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=filename,
                Body=body,
                ContentType='application/x-ndjson'
            )
        )
        print(f"✅ Uploaded batch of {len(data_batch)} flights to S3: {filename}")
        
    except Exception as e:
        print(f"❌ Failed to upload to S3: {e}")

@app.agent(flight_topic)
async def process_flights(flights):
    global LAST_FLUSH_TIME
    
    async for flight in flights:
        print(f"📨 Received: {flight.get('callsign')}")
        BUFFER.append(flight)
        
        # Flush if buffer is full
        if len(BUFFER) >= BUFFER_SIZE:
            await upload_to_s3(list(BUFFER))
            BUFFER.clear()
            LAST_FLUSH_TIME = datetime.now()
            
    # Note: Faunts agents run forever. 
    # Logic to flush on time interval would usually go in a @app.timer
    
@app.timer(interval=5.0)
async def periodic_flush():
    """Flush buffer every 5 seconds if there data"""
    global LAST_FLUSH_TIME
    if BUFFER and (datetime.now() - LAST_FLUSH_TIME).total_seconds() > 5:
        print(f"⏰ Timeout flush: {len(BUFFER)} items")
        await upload_to_s3(list(BUFFER))
        BUFFER.clear()
        LAST_FLUSH_TIME = datetime.now()

if __name__ == '__main__':
    app.main()
