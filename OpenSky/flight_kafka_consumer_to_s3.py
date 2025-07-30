from kafka import KafkaConsumer
import json
import boto3
import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

consumer= KafkaConsumer(
    'realtime-flights',
    bootstrap_servers= 'localhost:9092',
    auto_offset_reset= 'latest',  # Changed from 'earliest' to 'latest'
    enable_auto_commit= True,
    group_id='flight-s3-consumer',  # Add this line
    value_deserializer= lambda x: json.loads(x.decode('utf-8'))
)
print(os.getenv('AWS_ACCESS_KEY_ID'))
# Use environment variables for AWS credentials
s3= boto3.client('s3', 
                 region_name='ap-south-1',
                 aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                 aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

bucket_name= 'realtimeflightstreamingbucket'

def get_s3_path():
    now= datetime.datetime.utcnow()
    return f"bronze/{now.strftime('%Y/%m/%d/%H')}/flights_{now.strftime('%Y%m%d%H%M%S')}.json"

def write_to_s3(flight_batch):
    key=get_s3_path()
    s3.put_object(
        Bucket= bucket_name,
        Key=key,
        Body= json.dumps(flight_batch)
    )
    
    print(f"✅ Wrote {len(flight_batch)} flights to s3://{bucket_name}/{key}")

def consume_and_store():
    buffer=[]
    batch_size= 300
    
    for message in consumer:
        buffer.append(message.value)
        
        if len(buffer) >= batch_size:
            write_to_s3(buffer)
            buffer.clear()
        
if __name__=="__main__":
    consume_and_store()