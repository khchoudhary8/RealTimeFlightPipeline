# import snowflake.connector
# import os
# from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives.asymmetric import rsa
# from cryptography.hazmat.primitives.asymmetric import dsa
# from cryptography.hazmat.primitives import serialization

# # Load the private key from a file
# with open("rsa_key.p8", "rb") as key:
#     p_key = serialization.load_pem_private_key(
#         key.read(),
#         password=b'8409734394Kh$@',
#         backend=default_backend()
#     )

# # Convert the private key to bytes
# pkb = p_key.private_bytes(
#     encoding=serialization.Encoding.DER,
#     format=serialization.PrivateFormat.PKCS8,
#     encryption_algorithm=serialization.NoEncryption()
# )

# # Connect to Snowflake
# ctx = snowflake.connector.connect(
#     user='KHCHOUDHARY8',
#     account='SIZUJDG-YT23888',
#     private_key=pkb
# )

# # Create a cursor
# cs = ctx.cursor()

# # Example query
# try:
#     cs.execute("select current_user()")
#     result = cs.fetchone()
#     print(result)
# finally:
#     cs.close()
#     ctx.close()


import os
import snowflake.connector
from cryptography.hazmat.primitives import serialization

# --- 1. Your Snowflake Details ---
SNOWFLAKE_ACCOUNT = 'pg43135.ap-southeast-1'
SNOWFLAKE_USER = 'KHCHOUDHARY8'
SNOWFLAKE_DATABASE = 'ECOMMERCE_DW'
SNOWFLAKE_SCHEMA = 'PUBLIC'
SNOWFLAKE_ROLE = 'ACCOUNTADMIN' # It's good practice to specify the role

# --- 2. Your Private Key Details (Update this part) ---

# 🔴 IMPORTANT: Replace this with the actual path to your private key file.
PRIVATE_KEY_FILE = 'rsa_keyy.p8'

# If your private key is encrypted with a passphrase, uncomment and set it here.
# For better security, load it from an environment variable or secrets manager.
# PRIVATE_KEY_PASSPHRASE = os.environ.get('PRIVATE_KEY_PASSPHRASE')
PRIVATE_KEY_PASSPHRASE = None

# --- 3. Code to Read the Key and Connect (No changes needed below) ---
try:
    with open(PRIVATE_KEY_FILE, "rb") as key_file:
        p_key = serialization.load_pem_private_key(
            key_file.read(),
            password=(
                PRIVATE_KEY_PASSPHRASE.encode() if PRIVATE_KEY_PASSPHRASE else None
            ),
        )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
except FileNotFoundError:
    print(f"❌ Error: Private key file not found at '{PRIVATE_KEY_FILE}'")
    exit()


# --- 4. Establish Connection ---
conn = None
try:
    print("Attempting to connect to Snowflake...")
    conn = snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        account=SNOWFLAKE_ACCOUNT,
        private_key=pkb,  # Pass the processed private key
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        role=SNOWFLAKE_ROLE,
    )

    print("✅ Connection successful!")
    
    # --- Execute a test query ---
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_VERSION();")
    snowflake_version = cursor.fetchone()[0]
    print(f"Snowflake Version: {snowflake_version}")

except Exception as e:
    print(f"❌ Connection Failed: {e}")

finally:
    if conn:
        conn.close()
        print("Connection closed.")