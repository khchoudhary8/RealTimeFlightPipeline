#!/usr/bin/env python3
"""
Silver to Gold Layer ETL
Loads cleaned flight data from S3 Silver layer into Snowflake Gold layer
"""

import boto3
import os
import json
import pandas as pd
from dotenv import load_dotenv
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from snowflake.connector.pandas_tools import write_pandas
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# S3 Configuration
s3 = boto3.client(
    "s3",
    region_name="ap-south-1",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

BUCKET_NAME = "realtimeflightstreamingbucket"
SILVER_PREFIX = "silver_flights/"

# Snowflake Configuration
SNOWFLAKE_CONFIG = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "database": os.getenv("SNOWFLAKE_DATABASE", "FLIGHT_ANALYTICS"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
}


def get_snowflake_connection():
    """Create Snowflake connection with auth fallback.

    Priority:
    1) Key-pair (SNOWFLAKE_PRIVATE_KEY_PATH)
    2) OAuth token (SNOWFLAKE_OAUTH_ACCESS_TOKEN)
    3) Username + password
    """
    try:
        config = dict(SNOWFLAKE_CONFIG)  # shallow copy we can mutate

        # 1) Key-pair authentication
        private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")

        if private_key_path and os.path.exists(private_key_path):
            try:
                # Load the private key from file (exact pattern from your sample)
                with open(private_key_path, "rb") as key_file:
                    p_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=(
                            # private_key_passphrase.encode() if private_key_passphrase else
                            None
                        ),
                    )

                # Convert the private key to bytes (exact pattern from your sample)
                pkb = p_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )

                # Connect to Snowflake (exact pattern from your sample) with optional insecure mode
                connect_kwargs = {
                    "user": config["user"],
                    "account": config["account"],
                    "private_key": pkb,
                    "disable_ocsp_checks": True,
                }

                conn = snowflake.connector.connect(**connect_kwargs)
                logger.info("🔐 Using key-pair authentication for Snowflake")
                logger.info("✅ Connected to Snowflake successfully")
                return conn

            except Exception as e:
                logger.error(f"❌ Error during key-pair connection: {e}")
                raise

        # 2) OAuth token
        oauth_token = os.getenv("SNOWFLAKE_OAUTH_ACCESS_TOKEN")
        if oauth_token:
            config["authenticator"] = "oauth"
            config["token"] = oauth_token
            config.pop("password", None)
            logger.info("🛡️ Using OAuth token authentication for Snowflake")
            conn = snowflake.connector.connect(**config)
            logger.info("✅ Connected to Snowflake successfully")
            return conn

        # 3) Username/password (may trigger MFA if required by account policies)
        # Optional insecure mode here as well
        insecure_flag = os.getenv("SNOWFLAKE_INSECURE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
        if insecure_flag:
            config["insecure_mode"] = True
            logger.warning("⚠️ SNOWFLAKE_INSECURE_MODE enabled: OCSP/cert revocation checks are relaxed")

        logger.info("🔑 Using username/password authentication for Snowflake")
        conn = snowflake.connector.connect(**config)
        logger.info("✅ Connected to Snowflake successfully")
        return conn

    except Exception as e:
        logger.error(f"❌ Failed to connect to Snowflake: {e}")
        raise


def create_snowflake_tables(conn):
    """Create analytics tables in Snowflake"""
    try:
        cursor = conn.cursor()

        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {SNOWFLAKE_CONFIG['database']}")
        cursor.execute(f"USE DATABASE {SNOWFLAKE_CONFIG['database']}")

        # Create schema if not exists
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SNOWFLAKE_CONFIG['schema']}")
        cursor.execute(f"USE SCHEMA {SNOWFLAKE_CONFIG['schema']}")

        # Create main flights table
        create_flights_table = """
        CREATE OR REPLACE TABLE flights_raw (
            icao24 VARCHAR(20),
            callsign VARCHAR(20),
            origin_country VARCHAR(50),
            time_position TIMESTAMP,
            longitude FLOAT,
            latitude FLOAT,
            baro_altitude FLOAT,
            velocity FLOAT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            partition_date DATE AS (DATE(time_position))
        ) CLUSTER BY (partition_date, origin_country)
        """

        cursor.execute(create_flights_table)
        logger.info("✅ Created flights_raw table")

        # Create analytics views
        create_analytics_views = """
        -- Daily flight counts by country
        CREATE OR REPLACE VIEW daily_flight_counts AS
        SELECT 
            partition_date,
            origin_country,
            COUNT(*) as flight_count,
            AVG(baro_altitude) as avg_altitude,
            AVG(velocity) as avg_velocity
        FROM flights_raw
        WHERE time_position IS NOT NULL
        GROUP BY partition_date, origin_country
        ORDER BY partition_date DESC, flight_count DESC;
        
        -- Hourly flight activity
        CREATE OR REPLACE VIEW hourly_flight_activity AS
        SELECT 
            partition_date,
            HOUR(time_position) as hour_of_day,
            COUNT(*) as flight_count,
            COUNT(DISTINCT icao24) as unique_aircraft
        FROM flights_raw
        WHERE time_position IS NOT NULL
        GROUP BY partition_date, HOUR(time_position)
        ORDER BY partition_date DESC, hour_of_day;
        
        -- Top airlines by flight count
        CREATE OR REPLACE VIEW top_airlines AS
        SELECT 
            SUBSTRING(callsign, 1, 3) as airline_code,
            origin_country,
            COUNT(*) as flight_count,
            AVG(baro_altitude) as avg_altitude,
            AVG(velocity) as avg_velocity
        FROM flights_raw
        WHERE callsign IS NOT NULL AND LENGTH(callsign) >= 3
        GROUP BY SUBSTRING(callsign, 1, 3), origin_country
        ORDER BY flight_count DESC
        LIMIT 50;
        """

        # Execute multiple CREATE VIEW statements separately
        statements = [s.strip() for s in create_analytics_views.split(";")]
        executed = 0
        for stmt in statements:
            if not stmt or stmt.startswith("--"):
                continue
            cursor.execute(stmt)
            executed += 1
        logger.info(f"✅ Created analytics views ({executed} statements)")

        cursor.close()

    except Exception as e:
        logger.error(f"❌ Error creating Snowflake tables: {e}")
        raise


def list_silver_objects():
    """List all objects in S3 silver layer"""
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=SILVER_PREFIX)
        objects = [obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".json")]
        logger.info(f"🔍 Found {len(objects)} objects in S3 silver layer")
        return objects
    except Exception as e:
        logger.error(f"❌ Error listing S3 objects: {e}")
        return []


def read_silver_data(objects):
    """Read and combine data from silver layer"""
    all_records = []

    for i, key in enumerate(objects):
        try:
            logger.info(f"📁 Processing file {i + 1}/{len(objects)}: {key}")
            response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)

            if isinstance(data, list):
                all_records.extend(data)
            else:
                all_records.append(data)

        except Exception as e:
            logger.error(f"❌ Error processing {key}: {e}")

    logger.info(f"📊 Total records collected: {len(all_records)}")
    return all_records


def transform_for_snowflake(records):
    """Transform data for Snowflake ingestion"""
    df = pd.DataFrame(records)

    # Convert time_position to datetime
    df["time_position"] = pd.to_datetime(df["time_position"], unit="s", errors="coerce")

    # Handle missing values
    df = df.dropna(subset=["longitude", "latitude"])

    # Ensure proper data types
    df["icao24"] = df["icao24"].astype(str)
    df["callsign"] = df["callsign"].astype(str)
    df["origin_country"] = df["origin_country"].astype(str)
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["baro_altitude"] = pd.to_numeric(df["baro_altitude"], errors="coerce")
    df["velocity"] = pd.to_numeric(df["velocity"], errors="coerce")

    logger.info(f"📊 Transformed DataFrame shape: {df.shape}")
    logger.info(f"📋 Columns: {list(df.columns)}")

    return df


def load_to_snowflake(conn, df):
    """Load data to Snowflake"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"USE DATABASE {SNOWFLAKE_CONFIG['database']}")
        cursor.execute(f"USE SCHEMA {SNOWFLAKE_CONFIG['schema']}")

        # Use write_pandas for efficient bulk loading
        success, nchunks, nrows, _ = write_pandas(
            conn,
            df,
            "FLIGHTS_RAW",
            database=SNOWFLAKE_CONFIG["database"],
            schema=SNOWFLAKE_CONFIG["schema"],
            auto_create_table=False,
            overwrite=False,
            quote_identifiers=False,
        )

        if success:
            logger.info(f"✅ Successfully loaded {nrows} rows to Snowflake in {nchunks} chunks")
        else:
            logger.error("❌ Failed to load data to Snowflake")

        cursor.close()

    except Exception as e:
        logger.error(f"❌ Error loading to Snowflake: {e}")
        raise


def main():
    """Main ETL process"""
    logger.info("🚀 Starting Silver to Gold ETL process...")

    try:
        # Connect to Snowflake
        conn = get_snowflake_connection()

        # Create tables and views
        create_snowflake_tables(conn)

        # Get silver layer data
        silver_objects = list_silver_objects()
        if not silver_objects:
            logger.warning("⚠️ No data found in silver layer")
            return

        # Read and transform data
        records = read_silver_data(silver_objects)
        if not records:
            logger.warning("⚠️ No valid records found")
            return

        df = transform_for_snowflake(records)

        # Load to Snowflake
        load_to_snowflake(conn, df)

        logger.info("✅ Silver to Gold ETL completed successfully!")

    except Exception as e:
        logger.error(f"❌ ETL process failed: {e}")
        raise
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
