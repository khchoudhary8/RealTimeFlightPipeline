#!/usr/bin/env python3
"""
Fix certificate validation issue by setting SNOWFLAKE_INSECURE_MODE=true
"""

import os
from dotenv import load_dotenv, set_key

def fix_cert_issue():
    """Set SNOWFLAKE_INSECURE_MODE to true to bypass certificate validation"""
    
    env_file = '.env'
    
    # Load existing .env file
    load_dotenv()
    
    # Set SNOWFLAKE_INSECURE_MODE to true
    set_key(env_file, 'SNOWFLAKE_INSECURE_MODE', 'true')
    
    print("✅ Set SNOWFLAKE_INSECURE_MODE=true in .env file")
    print("⚠️  This relaxes certificate validation checks - use only for development")
    
    # Verify the setting
    load_dotenv(override=True)  # Reload to get updated values
    insecure_mode = os.getenv('SNOWFLAKE_INSECURE_MODE', 'false')
    print(f"🔍 Current SNOWFLAKE_INSECURE_MODE value: {insecure_mode}")
    
    if insecure_mode.lower() == 'true':
        print("✅ Certificate issue should now be resolved")
        print("🔄 Try running the Silver to Gold ETL again")
    else:
        print("❌ SNOWFLAKE_INSECURE_MODE not set correctly")

if __name__ == "__main__":
    fix_cert_issue()
