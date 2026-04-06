import boto3
import json
import polars as pl
from dagster import asset, Output
from config.settings import settings
from deltalake import write_deltalake

@asset
def silver_flights(raw_flight_files):
    """
    Reads the list of raw files, merges them, cleans data,
    deduplicates, and saves as a Delta Table to Silver Layer.
    """
    if not raw_flight_files:
        return Output(None, metadata={"status": "No new files to process"})

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

    all_data = []
    
    # Read files from S3
    print(f"[PROGRESS] Processing {len(raw_flight_files)} files...")
    
    for key in raw_flight_files:
        try:
            obj = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
            content = obj['Body'].read().decode('utf-8')
            
            # Bronze format is NDJSON (newline delimited JSON)
            for line in content.strip().split('\n'):
                if line:
                    all_data.append(json.loads(line))
        except Exception as e:
            print(f"[ERROR] Error reading {key}: {e}")

    if not all_data:
        return Output(None, metadata={"status": "No data found in files"})

    # --- Transformation (The "Silver" Polish) ---
    df = pl.DataFrame(all_data)
    
    # Cast types (Polars infers, but explicit is better)
    df = df.with_columns([
        pl.col("longitude").cast(pl.Float64),
        pl.col("latitude").cast(pl.Float64),
        pl.col("baro_altitude").cast(pl.Float64),
        pl.col("velocity").cast(pl.Float64),
        pl.col("time_position").cast(pl.Int64)
    ])
    
    # Add partition column for Delta Lake
    # If we have time_position, we can use it. Otherwise use current date.
    # time_position is unix timestamp.
    df = df.with_columns(
        (pl.col("time_position") * 1000).cast(pl.Datetime).dt.date().alias("partition_date")
    )

    # Deduplicate by Aircraft + Timestamp (ensure no repeat observations)
    initial_count = len(df)
    df = df.unique(subset=["icao24", "time_position"])
    deduped_count = len(df)

    # Convert to Pandas for deltalake writer
    df_pd = df.to_pandas()

    # --- Write to Delta Lake ---
    delta_table_path = f"s3://{settings.S3_BUCKET_NAME}/silver/delta_flights"
    
    storage_options = {
        "AWS_ACCESS_KEY_ID": settings.AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": settings.AWS_SECRET_ACCESS_KEY,
        "AWS_REGION": settings.AWS_REGION,
    }
    
    print(f"[S3] Writing {len(df_pd)} unique observations to Delta Table: {delta_table_path}")
    
    write_deltalake(
        delta_table_path,
        df_pd,
        mode="overwrite", # In dev, overwrite ensures we don't double-count historical Bronze files on every run
        partition_by=["partition_date"],
        storage_options=storage_options
    )

    return Output(
        delta_table_path, # Return the table path
        metadata={
            "input_files": len(raw_flight_files),
            "rows_read": initial_count,
            "rows_written": deduped_count,
            "s3_path": delta_table_path,
            "table_format": "Delta Lake"
        }
    )
