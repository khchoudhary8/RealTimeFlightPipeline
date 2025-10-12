#!/usr/bin/env python3
"""
Flight Analytics Dashboard
Provides analytics and insights from the Gold layer data
"""

import snowflake.connector
import pandas as pd
import os
from dotenv import load_dotenv
import logging
from cryptography.hazmat.primitives import serialization

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

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
    """Create Snowflake connection with key-pair authentication"""
    try:
        config = dict(SNOWFLAKE_CONFIG)  # shallow copy we can mutate

        # Try key-pair authentication first
        private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")

        if private_key_path and os.path.exists(private_key_path):
            try:
                # Load the private key from file
                with open(private_key_path, "rb") as key_file:
                    p_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=None,  # No password for your key
                    )

                # Convert the private key to bytes
                pkb = p_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )

                # Connect to Snowflake with key-pair authentication
                connect_kwargs = {
                    "user": config["user"],
                    "account": config["account"],
                    "private_key": pkb,
                    "disable_ocsp_checks": True,
                }

                # Add insecure mode for S3 operations if enabled
                insecure_flag = os.getenv("SNOWFLAKE_INSECURE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
                if insecure_flag:
                    connect_kwargs["insecure_mode"] = True
                    connect_kwargs["ocsp_fail_open"] = True

                conn = snowflake.connector.connect(**connect_kwargs)
                logger.info("✅ Connected to Snowflake successfully with key-pair authentication")
                return conn

            except Exception as e:
                logger.error(f"❌ Key-pair authentication failed: {e}")
                # Fall back to password authentication
                pass

        # Fall back to password authentication
        logger.info("Using password authentication for Snowflake")
        conn = snowflake.connector.connect(**config)
        logger.info("✅ Connected to Snowflake successfully")
        return conn

    except Exception as e:
        logger.error(f"❌ Failed to connect to Snowflake: {e}")
        raise


def get_daily_flight_summary(conn):
    """Get daily flight summary"""
    query = """
    SELECT 
        partition_date,
        COUNT(*) as total_flights,
        COUNT(DISTINCT icao24) as unique_aircraft,
        AVG(baro_altitude) as avg_altitude,
        AVG(velocity) as avg_velocity,
        COUNT(DISTINCT origin_country) as countries
    FROM flights_raw
    WHERE time_position IS NOT NULL
    GROUP BY partition_date
    ORDER BY partition_date DESC
    LIMIT 7
    """

    df = pd.read_sql(query, conn)
    return df


def get_country_breakdown(conn):
    """Get flight breakdown by country"""
    query = """
    SELECT 
        origin_country,
        COUNT(*) as flight_count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage,
        AVG(baro_altitude) as avg_altitude,
        AVG(velocity) as avg_velocity
    FROM flights_raw
    WHERE time_position IS NOT NULL
    GROUP BY origin_country
    ORDER BY flight_count DESC
    LIMIT 10
    """

    df = pd.read_sql(query, conn)
    return df


def get_hourly_activity(conn):
    """Get hourly flight activity"""
    query = """
    SELECT 
        HOUR(time_position) as hour_of_day,
        COUNT(*) as flight_count,
        COUNT(DISTINCT icao24) as unique_aircraft
    FROM flights_raw
    WHERE time_position IS NOT NULL
    GROUP BY HOUR(time_position)
    ORDER BY hour_of_day
    """

    df = pd.read_sql(query, conn)
    return df


def get_top_airlines(conn):
    """Get top airlines by flight count"""
    query = """
    SELECT 
        airline_code,
        origin_country,
        flight_count,
        ROUND(avg_altitude, 2) as avg_altitude,
        ROUND(avg_velocity, 2) as avg_velocity
    FROM top_airlines
    LIMIT 15
    """

    df = pd.read_sql(query, conn)
    return df


def get_altitude_velocity_stats(conn):
    """Get altitude and velocity statistics"""
    query = """
    SELECT 
        ROUND(MIN(baro_altitude), 2) as min_altitude,
        ROUND(MAX(baro_altitude), 2) as max_altitude,
        ROUND(AVG(baro_altitude), 2) as avg_altitude,
        ROUND(MIN(velocity), 2) as min_velocity,
        ROUND(MAX(velocity), 2) as max_velocity,
        ROUND(AVG(velocity), 2) as avg_velocity
    FROM flights_raw
    WHERE baro_altitude IS NOT NULL AND velocity IS NOT NULL
    """

    df = pd.read_sql(query, conn)
    return df


def print_dashboard(conn):
    """Print analytics dashboard"""
    print("\n" + "=" * 80)
    print("🛩️  FLIGHT ANALYTICS DASHBOARD")
    print("=" * 80)

    try:
        # Daily Summary
        print("\n📊 DAILY FLIGHT SUMMARY (Last 7 Days)")
        print("-" * 50)
        daily_df = get_daily_flight_summary(conn)
        if not daily_df.empty:
            for _, row in daily_df.iterrows():
                print(
                    f"📅 {row['PARTITION_DATE']}: {row['TOTAL_FLIGHTS']:,} flights | "
                    f"{row['UNIQUE_AIRCRAFT']:,} aircraft | "
                    f"Avg Alt: {row['AVG_ALTITUDE']:.0f}m | "
                    f"Avg Speed: {row['AVG_VELOCITY']:.0f} m/s"
                )
        else:
            print("No data available")

        # Country Breakdown
        print("\n🌍 TOP COUNTRIES BY FLIGHT COUNT")
        print("-" * 50)
        country_df = get_country_breakdown(conn)
        if not country_df.empty:
            for _, row in country_df.iterrows():
                print(
                    f"🇮🇳 {row['ORIGIN_COUNTRY']}: {row['FLIGHT_COUNT']:,} flights "
                    f"({row['PERCENTAGE']}%) | "
                    f"Avg Alt: {row['AVG_ALTITUDE']:.0f}m"
                )
        else:
            print("No data available")

        # Top Airlines
        print("\n✈️  TOP AIRLINES BY FLIGHT COUNT")
        print("-" * 50)
        airline_df = get_top_airlines(conn)
        if not airline_df.empty:
            for _, row in airline_df.iterrows():
                print(
                    f"🛫 {row['AIRLINE_CODE']} ({row['ORIGIN_COUNTRY']}): "
                    f"{row['FLIGHT_COUNT']:,} flights | "
                    f"Avg Alt: {row['AVG_ALTITUDE']:.0f}m | "
                    f"Avg Speed: {row['AVG_VELOCITY']:.0f} m/s"
                )
        else:
            print("No data available")

        # Altitude & Velocity Stats
        print("\n📈 ALTITUDE & VELOCITY STATISTICS")
        print("-" * 50)
        stats_df = get_altitude_velocity_stats(conn)
        if not stats_df.empty:
            row = stats_df.iloc[0]
            print(
                f"🔼 Altitude: {row['MIN_ALTITUDE']:.0f}m - {row['MAX_ALTITUDE']:.0f}m "
                f"(Avg: {row['AVG_ALTITUDE']:.0f}m)"
            )
            print(
                f"🏃 Velocity: {row['MIN_VELOCITY']:.0f} - {row['MAX_VELOCITY']:.0f} m/s "
                f"(Avg: {row['AVG_VELOCITY']:.0f} m/s)"
            )
        else:
            print("No data available")

        # Hourly Activity
        print("\n🕐 HOURLY FLIGHT ACTIVITY")
        print("-" * 50)
        hourly_df = get_hourly_activity(conn)
        if not hourly_df.empty:
            for _, row in hourly_df.iterrows():
                hour = int(row["HOUR_OF_DAY"])
                print(
                    f"🕐 {hour:02d}:00 - {hour + 1:02d}:00: {row['FLIGHT_COUNT']:,} flights "
                    f"({row['UNIQUE_AIRCRAFT']:,} aircraft)"
                )
        else:
            print("No data available")

        print("\n" + "=" * 80)
        print("✅ Dashboard generated successfully!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ Error generating dashboard: {e}")


def main():
    """Main dashboard function"""
    try:
        conn = get_snowflake_connection()
        print_dashboard(conn)
        conn.close()
    except Exception as e:
        logger.error(f"❌ Dashboard failed: {e}")


if __name__ == "__main__":
    main()
