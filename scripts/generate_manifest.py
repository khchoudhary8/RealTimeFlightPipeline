import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path, override=True)

# Path to dbt project
project_dir = os.path.join(os.path.dirname(__file__), '..', 'dbt_project')
profiles_dir = project_dir

print(f"Loading .env from: {env_path}")
print(f"SNOWFLAKE_ACCOUNT: {os.getenv('SNOWFLAKE_ACCOUNT')}") # Debug
print("🚀 Running dbt compile to generate manifest.json...")

# Run dbt compile
try:
    result = subprocess.run(
        f"dbt compile --project-dir \"{project_dir}\" --profiles-dir \"{profiles_dir}\"",
        check=True,
        capture_output=True,
        text=True,
        shell=True,
        env=os.environ.copy() # Explicitly pass environment
    )
    print(result.stdout)
    print("✅ dbt compile successful!")
except subprocess.CalledProcessError as e:
    print("❌ dbt compile failed!")
    print(e.stdout)
    print(e.stderr)
