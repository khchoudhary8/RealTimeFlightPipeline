import boto3
import snowflake.connector
from config.settings import settings

def test_s3():
    print(f"--- Testing S3 with Bucket: {settings.S3_BUCKET_NAME} ---")
    print(f"Access Key ID: {settings.AWS_ACCESS_KEY_ID[:5]}...{settings.AWS_ACCESS_KEY_ID[-5:] if settings.AWS_ACCESS_KEY_ID else 'None'}")
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        response = s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME, MaxKeys=5)
        print("✅ S3 Connection Successful!")
        print(f"Files found: {len(response.get('Contents', []))}")
    except Exception as e:
        print(f"❌ S3 Error: {e}")

def test_snowflake():
    print(f"\n--- Testing Snowflake with Database: {settings.SNOWFLAKE_DATABASE} ---")
    try:
        conn = snowflake.connector.connect(
            user=settings.SNOWFLAKE_USER,
            password=settings.SNOWFLAKE_PASSWORD,
            account=settings.SNOWFLAKE_ACCOUNT,
            warehouse=settings.SNOWFLAKE_WAREHOUSE,
            role=settings.SNOWFLAKE_ROLE,
            insecure_mode=True
        )
        print("✅ Snowflake Connection Successful!")
        cursor = conn.cursor()
        print(f"Creating database {settings.SNOWFLAKE_DATABASE}...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.SNOWFLAKE_DATABASE}")
        cursor.execute("SHOW DATABASES")
        dbs = [row[1] for row in cursor.fetchall()]
        print(f"Available Databases: {dbs}")
        if settings.SNOWFLAKE_DATABASE.upper() in [db.upper() for db in dbs]:
            print(f"✅ Database '{settings.SNOWFLAKE_DATABASE}' exists.")
        else:
            print(f"❌ Database '{settings.SNOWFLAKE_DATABASE}' NOT found.")
        conn.close()
    except Exception as e:
        print(f"❌ Snowflake Error: {e}")

if __name__ == "__main__":
    test_s3()
    test_snowflake()
