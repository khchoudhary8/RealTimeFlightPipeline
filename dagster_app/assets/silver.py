from dagster import asset, MaterializeResult, ConfigurableResource
import boto3
import json
from datetime import datetime
from dagster_app.constants import BUCKET_NAME, BRONZE_PREFIX, BRONZE_PROCESSED_PREFIX, SILVER_PREFIX
from deltalake import write_deltalake
from Faust.transformation_utils import filter_valid_flights, generate_silver_key
from schemas.flight_schema import FlightRecord


@asset
def silver_flights(context, s3: ConfigurableResource):
    """
    Reads JSON files from Bronze (S3), validates with Pydantic,
    writes to Silver (Delta Lake), and moves processed files.
    """
    s3_client = boto3.client(
        "s3",
        region_name=s3.region_name,
        aws_access_key_id=s3.aws_access_key_id,
        aws_secret_access_key=s3.aws_secret_access_key,
    )

    # 1. List files in Bronze
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=BRONZE_PREFIX)
    objects = [obj for obj in response.get("Contents", []) if obj["Key"].endswith(".json")]

    if not objects:
        context.log.info("No new files in Bronze layer.")
        return MaterializeResult(metadata={"files_processed": 0})

    context.log.info(f"Found {len(objects)} files to process.")

    all_records = []
    processed_keys = []

    # 2. Read and Parse
    for obj in objects:
        key = obj["Key"]
        try:
            resp = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            content = resp["Body"].read().decode("utf-8")
            data = json.loads(content)

            # Handle both list and single object
            if isinstance(data, list):
                raw_records = data
            else:
                raw_records = [data]

            # Filter valid flights (with coordinates)
            valid_records = filter_valid_flights(raw_records)
            all_records.extend(valid_records)
            processed_keys.append(key)

            context.log.debug(f"Processed {key}: {len(valid_records)} valid flights")
        except Exception as e:
            context.log.error(f"Failed to read {key}: {e}")

    if not all_records:
        context.log.warning("No valid records found in files.")
        return MaterializeResult(metadata={"files_processed": len(processed_keys), "records": 0})

    # 3. Validate with Pydantic
    try:
        validated_records = []
        for record in all_records:
            try:
                flight = FlightRecord(**record)
                validated_records.append(flight.model_dump())
            except Exception as e:
                context.log.warning(f"Invalid flight record: {e}")
                continue
    except Exception as e:
        context.log.error(f"Validation failed: {e}")
        return MaterializeResult(metadata={"error": str(e), "files_processed": 0, "records_written": 0})

    if not validated_records:
        context.log.warning("No records passed validation.")
        return MaterializeResult(metadata={"files_processed": len(processed_keys), "records": 0})

    import pandas as pd

    df = pd.DataFrame(validated_records)

    # Add partition_date column
    if "time_position" in df.columns and pd.api.types.is_datetime64_any_dtype(df["time_position"]):
        df["partition_date"] = df["time_position"].dt.date
    else:
        df["partition_date"] = datetime.utcnow().date()

    context.log.info(f"Processing {len(df)} valid records after Pydantic validation.")

    # 4. Write to Delta Lake (S3)
    delta_path = f"s3://{BUCKET_NAME}/{SILVER_PREFIX}"

    storage_options = {
        "AWS_ACCESS_KEY_ID": s3.aws_access_key_id,
        "AWS_SECRET_ACCESS_KEY": s3.aws_secret_access_key,
        "AWS_REGION": s3.region_name,
    }

    try:
        write_deltalake(delta_path, df, mode="append", partition_by=["partition_date"], storage_options=storage_options)
        context.log.info(f"Wrote {len(df)} records to Delta Lake at {delta_path}")
    except Exception as e:
        context.log.error(f"Failed to write Delta Lake: {e}")
        raise

    # 5. Move Processed Files
    move_errors = 0
    for key in processed_keys:
        new_key = key.replace(BRONZE_PREFIX, BRONZE_PROCESSED_PREFIX, 1)
        try:
            s3_client.copy_object(Bucket=BUCKET_NAME, CopySource={"Bucket": BUCKET_NAME, "Key": key}, Key=new_key)
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=key)
        except Exception as e:
            context.log.error(f"Failed to move {key} to processed: {e}")
            move_errors += 1

    context.add_output_metadata(
        {
            "files_processed": len(processed_keys),
            "records_written": len(df),
            "delta_path": delta_path,
            "move_errors": move_errors,
        }
    )

    return df
