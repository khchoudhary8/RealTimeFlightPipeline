from dagster import asset, Output
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import pandas as pd
from deltalake import DeltaTable
from config.settings import settings
import os

def get_snowflake_connection():
    """Establishes connection to Snowflake using Key-Pair Auth if available."""
    config = {
        'user': settings.SNOWFLAKE_USER,
        'account': settings.SNOWFLAKE_ACCOUNT,
        'warehouse': settings.SNOWFLAKE_WAREHOUSE,
        'database': settings.SNOWFLAKE_DATABASE,
        'schema': settings.SNOWFLAKE_SCHEMA,
        'role': settings.SNOWFLAKE_ROLE,
    }

    private_key_path = settings.SNOWFLAKE_PRIVATE_KEY_PATH
    
    if private_key_path and os.path.exists(private_key_path):
        print("[AUTH] Using key-pair authentication for Snowflake")
        with open(private_key_path, "rb") as key_file:
            p_key = serialization.load_pem_private_key(
                key_file.read(),
                password=settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.encode() if settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE else None,
                backend=default_backend()
            )
        
        pkb = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        config['private_key'] = pkb
    else:
        print("[AUTH] Using password authentication for Snowflake")
        config['password'] = settings.SNOWFLAKE_PASSWORD

    # OCSP Fix
    config['insecure_mode'] = True
    return snowflake.connector.connect(**config)

@asset(key_prefix=["snowflake", "raw"])
def raw_flights_table(silver_flights):
    """
    Reads Silver Delta Table, loads to Snowflake FLIGHTS_RAW table.
    serves as source for dbt.
    """
    if not silver_flights:
         return Output(None, metadata={"status": "No silver data path provided"})

    # 1. Read Silver Delta Table from S3
    delta_table_path = silver_flights
    print(f"[FETCH] Reading Silver data from Delta Table: {delta_table_path}")
    
    storage_options = {
        "AWS_ACCESS_KEY_ID": settings.AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": settings.AWS_SECRET_ACCESS_KEY,
        "AWS_REGION": settings.AWS_REGION,
    }
    
    try:
        dt = DeltaTable(delta_table_path, storage_options=storage_options)
        df_pd = dt.to_pandas()
    except Exception as e:
        print(f"[ERROR] Error reading Delta Table: {e}")
        raise

    if df_pd.empty:
        return Output(None, metadata={"status": "Delta Table is empty"})

    # Transform for Snowflake
    df_pd['processed_at'] = pd.Timestamp.now()
    
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Ensure Database and Schema exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.SNOWFLAKE_DATABASE}")
        cursor.execute(f"USE DATABASE {settings.SNOWFLAKE_DATABASE}")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.SNOWFLAKE_SCHEMA}")
        cursor.execute(f"USE SCHEMA {settings.SNOWFLAKE_SCHEMA}")
        
        # 2. Drop + Recreate table for clean schema
        cursor.execute("DROP TABLE IF EXISTS FLIGHTS_RAW")
        print("[CLEAN] Cleaned schema for reload")

        # 3. Create Table with fresh schema
        create_table_sql = f"""
        CREATE TABLE {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA}.FLIGHTS_RAW (
            icao24 VARCHAR(20),
            callsign VARCHAR(20),
            origin_country VARCHAR(50),
            time_position TIMESTAMP,
            longitude FLOAT,
            latitude FLOAT,
            baro_altitude FLOAT,
            velocity FLOAT,
            processed_at TIMESTAMP,
            partition_date VARCHAR(10)
        )
        """
        cursor.execute(create_table_sql)

        # 4. Load Data
        print(f"[LOAD] Loading {len(df_pd)} rows to Snowflake...")
        df_pd.columns = [c.upper() for c in df_pd.columns]
        
        cols_to_keep = ['ICAO24', 'CALLSIGN', 'ORIGIN_COUNTRY', 'TIME_POSITION', 
                        'LONGITUDE', 'LATITUDE', 'BARO_ALTITUDE', 'VELOCITY', 'PARTITION_DATE']
        
        available_cols = [c for c in cols_to_keep if c in df_pd.columns]
        df_upload = df_pd[available_cols].copy()
        
        if 'TIME_POSITION' in df_upload.columns:
             # Convert to datetime, coercing errors.
             # If it's already datetime, this is safe.
             # If it's int (Unix timestamp), unit='s' usually works, but OpenSky is seconds.
             # However, if Polars read it as int/float, we need to be careful.
             
             # Check if numeric (int/float)
             if pd.api.types.is_numeric_dtype(df_upload['TIME_POSITION']):
                 df_upload['TIME_POSITION'] = pd.to_datetime(df_upload['TIME_POSITION'], unit='s')
             else:
                  # Already datetime or string? Ensure datetime64[ns]
                 df_upload['TIME_POSITION'] = pd.to_datetime(df_upload['TIME_POSITION'])

        # Ensure processed_at is also compatible
        df_upload['PROCESSED_AT'] = pd.Timestamp.now() 

        # Ensure PARTITION_DATE is a proper date string (Delta Lake stores it as epoch int)
        # write_pandas uses Parquet staging and can't cast raw ints to DATE,
        # so we convert to 'YYYY-MM-DD' strings which Snowflake loads cleanly.
        if 'PARTITION_DATE' in df_upload.columns:
            if pd.api.types.is_numeric_dtype(df_upload['PARTITION_DATE']):
                df_upload['PARTITION_DATE'] = pd.to_datetime(df_upload['PARTITION_DATE'], unit='ms').dt.strftime('%Y-%m-%d')
            elif pd.api.types.is_datetime64_any_dtype(df_upload['PARTITION_DATE']):
                df_upload['PARTITION_DATE'] = df_upload['PARTITION_DATE'].dt.strftime('%Y-%m-%d')
            # else: already string, leave as-is

        success, nchunks, nrows, _ = write_pandas(
            conn,
            df_upload,
            'FLIGHTS_RAW',
            database=settings.SNOWFLAKE_DATABASE,
            schema=settings.SNOWFLAKE_SCHEMA,
            quote_identifiers=False
        )
        print(f"[SUCCESS] Loaded {nrows} rows.")

        # 4. Create Analytics Views (Gold Logic)
        views_sql = [
            """
            CREATE OR REPLACE VIEW DAILY_FLIGHT_COUNTS AS
            SELECT 
                partition_date,
                origin_country,
                COUNT(*) as flight_count,
                AVG(baro_altitude) as avg_altitude,
                AVG(velocity) as avg_velocity
            FROM FLIGHTS_RAW
            WHERE time_position IS NOT NULL
            GROUP BY partition_date, origin_country
            ORDER BY partition_date DESC, flight_count DESC
            """,
            """
            CREATE OR REPLACE VIEW TOP_AIRLINES AS
            SELECT 
                SUBSTRING(callsign, 1, 3) as airline_code,
                origin_country,
                COUNT(*) as flight_count
            FROM FLIGHTS_RAW
            WHERE callsign IS NOT NULL
            GROUP BY SUBSTRING(callsign, 1, 3), origin_country
            ORDER BY flight_count DESC
            LIMIT 50
            """
        ]
        
        for sql in views_sql:
            cursor.execute(sql)
        
        print("[GOLD] Gold Views Created/Updated.")

    finally:
        conn.close()

    return Output(
        nrows,
        metadata={
            "snowflake_table": "FLIGHTS_RAW",
            "rows_loaded": nrows,
            "source_format": "Delta Lake"
        }
    )
