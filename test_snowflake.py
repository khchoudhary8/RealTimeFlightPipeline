import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    load_dotenv()
    
    base_account = os.getenv('SNOWFLAKE_ACCOUNT')
    # Try multiple account formats if the raw one fails
    account_variations = [
        base_account,
        f"{base_account}.ap-south-1.aws",
        f"{base_account}.ap-south-1",
        f"{base_account}.aws",
    ]
    
    user = os.getenv('SNOWFLAKE_USER')
    password = os.getenv('SNOWFLAKE_PASSWORD')
    
    print(f"User: {user}")
    print(f"Base Account: {base_account}")
    
    for account in account_variations:
        print(f"\n--- Testing Account Identifier: {account} ---")
        config = {
            'user': user,
            'account': account,
            'password': password,
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
            'database': os.getenv('SNOWFLAKE_DATABASE'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA'),
            'role': os.getenv('SNOWFLAKE_ROLE'),
            'insecure_mode': True
        }
        
        try:
            conn = snowflake.connector.connect(**config)
            print(f"✅ Connection successful with: {account}")
            
            cursor = conn.cursor()
            cursor.execute("SELECT current_version()")
            version = cursor.fetchone()
            print(f"Snowflake version: {version[0]}")
            
            # Check for table
            cursor.execute(f"SHOW TABLES LIKE 'FLIGHTS_RAW' IN SCHEMA {config['database']}.{config['schema']}")
            table = cursor.fetchone()
            if table:
                print("✅ Table 'FLIGHTS_RAW' found.")
            else:
                print("❌ Table 'FLIGHTS_RAW' NOT found.")
                
            conn.close()
            print(f"\n✨ SUCCESS! Correct account identifier is: {account}")
            return account
        except Exception as e:
            print(f"❌ Failed: {e}")
            
    print("\n❌ All account variations failed.")
    return None

if __name__ == "__main__":
    test_connection()
