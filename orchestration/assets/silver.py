import boto3
import json
import io
import polars as pl
import pandas as pd
from dagster import asset, Output
from config.settings import settings
from .bronze import raw_flight_files
from deltalake import write_deltalake, DeltaTable
from datetime import datetime

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
    print(f"🔄 Processing {len(raw_flight_files)} files...")
    
    for key in raw_flight_files:
        try:
            obj = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
            content = obj['Body'].read().decode('utf-8')
            
            # Bronze format is NDJSON (newline delimited JSON)
            for line in content.strip().split('\n'):
                if line:
                    all_data.append(json.loads(line))
        except Exception as e:
            print(f"⚠️ Error reading {key}: {e}")

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

    # Deduplicate
    initial_count = len(df)
    df = df.unique()
    deduped_count = len(df)

    # Convert to Pandas for deltalake writer (it supports Arrow/Pandas)
    df_pd = df.to_pandas()

    # --- Write to Delta Lake ---
    # We write to a Delta Table path in S3
    delta_table_path = f"s3://{settings.S3_BUCKET_NAME}/silver/delta_flights"
    
    storage_options = {
        "AWS_ACCESS_KEY_ID": settings.AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": settings.AWS_SECRET_ACCESS_KEY,
        "AWS_REGION": settings.AWS_REGION,
    }
    
    print(f"💾 Writing {len(df_pd)} rows to Delta Table: {delta_table_path}")
    
    write_deltalake(
        delta_table_path,
        df_pd,
        mode="append",
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
