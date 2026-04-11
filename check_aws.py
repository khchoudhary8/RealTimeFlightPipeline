import boto3
from config.settings import settings

def inspect_aws_env():
    print(f"--- Checking S3 Bucket: {settings.S3_BUCKET_NAME} ---")
    
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        sts = boto3.client(
            'sts',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Identity Check
        identity = sts.get_caller_identity()
        print(f"✅ AWS Account ID: {identity['Account']}")
        print(f"✅ IAM ARN: {identity['Arn']}")

        # List EVERYTHING in the bucket
        print(f"\nScanning all objects in '{settings.S3_BUCKET_NAME}'...")
        response = s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME)
        
        objs = response.get('Contents', [])
        print(f"📍 Found {len(objs)} total objects in bucket.")
        
        for obj in objs[:20]:
            print(f" - {obj['Key']} ({obj['Size']} bytes)")
            
    except Exception as e:
        print(f"❌ Error during inspection: {e}")

if __name__ == "__main__":
    inspect_aws_env()
