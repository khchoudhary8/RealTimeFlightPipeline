from dagster import asset, Output, AssetObservation
import boto3
from config.settings import settings

@asset
def raw_flight_files():
    """
    Lists all raw JSON flight files currently in the Bronze S3 bucket.
    Acts as the entry point for our pipeline.
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

    # List objects in the bronze prefix
    # In a real system, we might only list *new* files or use a sensor.
    # For this baby step, we list everything to verify visibility.
    try:
        response = s3.list_objects_v2(
            Bucket=settings.S3_BUCKET_NAME,
            Prefix="bronze/raw_flights/"
        )
        files = [obj["Key"] for obj in response.get("Contents", [])]
    except Exception as e:
        # Fallback for testing if credentials aren't set
        print(f"S3 Error: {e}")
        files = []
    
    # Log metadata to Dagster UI
    return Output(
        files, 
        metadata={
            "file_count": len(files),
            "example_file": files[0] if files else "None"
        }
    )
