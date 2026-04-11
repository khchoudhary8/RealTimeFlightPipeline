import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import os
import sys
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings


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
        config['password'] = settings.SNOWFLAKE_PASSWORD

    config['insecure_mode'] = True
    return snowflake.connector.connect(**config)


@st.cache_data(ttl=600)
def query_snowflake(query, params=None):
    """Execute a query and return a DataFrame. Cached for 10 minutes.
    Uses Snowflake's native fetch_pandas_all() to avoid C int overflow on large numbers.
    """
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        df = cursor.fetch_pandas_all()
        return df
    finally:
        conn.close()


def get_all_flights():
    """Get all flight data for advanced analytics."""
    return query_snowflake("""
        SELECT ICAO24, CALLSIGN, ORIGIN_COUNTRY, TIME_POSITION,
               LONGITUDE, LATITUDE, BARO_ALTITUDE, VELOCITY,
               PROCESSED_AT, PARTITION_DATE
        FROM FLIGHTS_RAW
        WHERE LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
        ORDER BY TIME_POSITION
    """)

def get_live_unique_flight_count():
    """Get the count of unique aircraft seen in the last 15 minutes."""
    df = query_snowflake("""
        SELECT COUNT(DISTINCT ICAO24) as unique_count
        FROM FLIGHTS_RAW
        WHERE TIME_POSITION > DATEADD(minute, -15, CURRENT_TIMESTAMP())
    """)
    return int(df.iloc[0]['UNIQUE_COUNT']) if not df.empty else 0


def get_recent_flights(minutes=15):
    """Get the latest position for each aircraft seen in the last N minutes."""
    return query_snowflake(f"""
        WITH latest_positions AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY ICAO24 ORDER BY TIME_POSITION DESC) as rn
            FROM FLIGHTS_RAW
            WHERE TIME_POSITION > DATEADD(minute, -{minutes}, CURRENT_TIMESTAMP())
        )
        SELECT ICAO24, CALLSIGN, ORIGIN_COUNTRY, TIME_POSITION,
               LONGITUDE, LATITUDE, BARO_ALTITUDE, VELOCITY,
               PARTITION_DATE
        FROM latest_positions
        WHERE rn = 1
        AND LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
        ORDER BY TIME_POSITION DESC
    """)


def get_flight_path(icao24):
    """Get the full path of a specific aircraft."""
    return query_snowflake(f"""
        SELECT ICAO24, CALLSIGN, TIME_POSITION,
               LONGITUDE, LATITUDE, BARO_ALTITUDE, VELOCITY
        FROM FLIGHTS_RAW
        WHERE ICAO24 = '{icao24}'
        AND LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
        ORDER BY TIME_POSITION
    """)
def get_flights_by_date(selected_date):
    """Get the latest position for each aircraft seen on a specific date."""
    return query_snowflake(f"""
        WITH latest_positions AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY ICAO24 ORDER BY TIME_POSITION DESC) as rn
            FROM FLIGHTS_RAW
            WHERE PARTITION_DATE = '{selected_date}'
        )
        SELECT ICAO24, CALLSIGN, ORIGIN_COUNTRY, TIME_POSITION,
               LONGITUDE, LATITUDE, BARO_ALTITUDE, VELOCITY,
               PARTITION_DATE
        FROM latest_positions
        WHERE rn = 1
        AND LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
        ORDER BY TIME_POSITION DESC
    """)
