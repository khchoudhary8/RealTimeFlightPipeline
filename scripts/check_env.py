import os
from dotenv import load_dotenv

# Force reload from the .env file
load_dotenv(override=True)

print(f"Current SNOWFLAKE_SCHEMA in .env: {os.getenv('SNOWFLAKE_SCHEMA')}")
