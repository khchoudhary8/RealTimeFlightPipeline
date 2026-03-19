# Snowflake Resource Definition
from dagster_snowflake import SnowflakeResource
import os

snowflake_resource = SnowflakeResource(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    database=os.getenv("SNOWFLAKE_DATABASE", "FLIGHT_ANALYTICS"),
    schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
)
