import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings

def get_snowflake_connection():
    config = {
        'user': settings.SNOWFLAKE_USER,
        'account': settings.SNOWFLAKE_ACCOUNT,
        'warehouse': settings.SNOWFLAKE_WAREHOUSE,
        'database': settings.SNOWFLAKE_DATABASE,
        'schema': settings.SNOWFLAKE_SCHEMA,
        'role': settings.SNOWFLAKE_ROLE,
        'insecure_mode': True
    }

    private_key_path = settings.SNOWFLAKE_PRIVATE_KEY_PATH
    if private_key_path and os.path.exists(private_key_path):
        with open(private_key_path, "rb") as key_file:
            password = settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.encode() if settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE else None
            p_key = serialization.load_pem_private_key(
                key_file.read(),
                password=password,
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

    return snowflake.connector.connect(**config)

def check_data():
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    try:
        print("🔍 Checking FLIGHTS_RAW table...")
        
        # 1. Count
        cursor.execute("SELECT COUNT(*) FROM FLIGHTS_RAW")
        count = cursor.fetchone()[0]
        print(f"📉 Total Rows: {count}")
        
        if count > 0:
            # 2. Time Range
            cursor.execute("SELECT MIN(TIME_POSITION), MAX(TIME_POSITION), CURRENT_TIMESTAMP() FROM FLIGHTS_RAW")
            min_ts, max_ts, current_ts = cursor.fetchone()
            print(f"⏱️ Time Range: {min_ts} to {max_ts}")
            print(f"🕒 Current DB Time: {current_ts}")
            
            # 3. Sample
            print("\n📋 Sample Data (Top 5):")
            cursor.execute("SELECT ICAO24, CALLSIGN, TIME_POSITION, LATITUDE, LONGITUDE FROM FLIGHTS_RAW LIMIT 5")
            for row in cursor.fetchall():
                print(row)
        else:
            print("⚠️ Table is empty!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_data()
