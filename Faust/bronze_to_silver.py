import boto3
import os
import json
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

load_dotenv()


s3 = boto3.client('s3', region_name='ap-south-1',
                  aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))


BUCKET_NAME='realtimeflightstreamingbucket'
raw_prefix ='bronze/'
silver_prefix ='silver_flights/'

def list_objects():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=raw_prefix)
    objects = [obj['Key'] for obj in response.get('Contents',[]) if obj['Key'].endswith('.json')]
    print(f"🔍 Found {len(objects)} objects in S3 with prefix '{raw_prefix}'")
    for obj in objects[:5]:  # Show first 5 objects
        print(f"  - {obj}")
    return objects

def read_json_from_s3(key):
    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    content = response['Body'].read().decode('utf-8')
    return json.loads(content)

def write_to_silver(dataframe, timestamp):  
    partition_path= timestamp.strftime('%Y/%m/%d/%H')
    out_key = f"{silver_prefix}{partition_path}/flights_{timestamp.strftime('%Y%m%d%H%M%S')}.json"
    s3.put_object(Bucket=BUCKET_NAME, Key=out_key, Body=dataframe.to_json(orient='records').encode('utf-8'))
    
    print(f"Wrote to silver layer: {out_key}")
    
def main():
    print("🚀 Starting bronze to silver transformation...")
    keys = list_objects()
    records = []
    
    if not keys:
        print("❌ No objects found in S3. Check if:")
        print("   1. S3 bucket exists: realtimeflightstreamingbucket")
        print("   2. Data was written to 'raw_flights/' prefix")
        print("   3. AWS credentials are correct")
        return
    
    print(f"📊 Processing {len(keys)} files...")
    
    for i, key in enumerate(keys):
        try:
            print(f"📁 Processing file {i+1}/{len(keys)}: {key}")
            data = read_json_from_s3(key)
            
            # Handle both single objects and arrays
            if isinstance(data, list):
                flights = data
                print(f"   📋 Found {len(flights)} flights in array")
            else:
                flights = [data]
                print("   📋 Found 1 flight object")
            
            valid_flights = 0
            for flight in flights:
                if flight.get('longitude') and flight.get('latitude'):
                    records.append(flight)
                    valid_flights += 1
            
            print(f"   ✅ Added {valid_flights} valid flights")
            
        except Exception as e:
            print(f"❌ Error processing {key}: {e}")
    
    print(f"\n📈 Total valid records collected: {len(records)}")
    
    if records:
        df = pd.DataFrame(records)
        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📋 Columns: {list(df.columns)}")
        
        now = datetime.utcnow()
        write_to_silver(df, now)
        print("✅ Silver layer transformation completed!")
    else:
        print("❌ No valid records found")
        print("💡 Check if flight data has 'longitude' and 'latitude' fields")
    
if __name__ == "__main__":
    main()
    
    
    
    
    
        