import boto3
from config.settings import settings

def check_s3_contents():
    print(f"--- Checking S3 Bucket: {settings.S3_BUCKET_NAME} ---")
    print(f"Region: {settings.AWS_REGION}")
    
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Test 1: List all prefixes
        print("\nChecking 'bronze/raw_flights/' prefix:")
        response = s3.list_objects_v2(
            Bucket=settings.S3_BUCKET_NAME,
            Prefix="bronze/raw_flights/"
        )
        
        objs = response.get('Contents', [])
        print(f"✅ Found {len(objs)} objects in 'bronze/raw_flights/'")
        for obj in objs[:10]:
            print(f" - {obj['Key']} ({obj['Size']} bytes)")
            
        # Test 2: List everything just in case
        if len(objs) == 0:
            print("\nSearching entire bucket for any files:")
            all_objs = s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME).get('Contents', [])
            print(f"Found {len(all_objs)} total objects in bucket.")
            for obj in all_objs[:10]:
                print(f" - {obj['Key']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_s3_contents()
