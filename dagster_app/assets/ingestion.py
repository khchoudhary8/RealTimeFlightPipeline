from dagster import asset, MaterializeResult, ConfigurableResource
import boto3
from dagster_app.constants import BUCKET_NAME, BRONZE_PREFIX


@asset
def bronze_flight_files(context, s3: ConfigurableResource):
    """
    Lists all JSON files in the Bronze S3 prefix.
    This asset materializes when new data arrives.
    """
    s3_client = boto3.client(
        "s3",
        region_name=s3.region_name,
        aws_access_key_id=s3.aws_access_key_id,
        aws_secret_access_key=s3.aws_secret_access_key,
    )

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=BRONZE_PREFIX)

    files = [obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".json")]

    context.log.info(f"Found {len(files)} files in bronze layer")

    # Return metadata for downstream assets
    return MaterializeResult(
        metadata={
            "file_count": len(files),
            "bucket": BUCKET_NAME,
            "prefix": BRONZE_PREFIX,
            "sample_files": files[:5] if files else [],
        }
    )
