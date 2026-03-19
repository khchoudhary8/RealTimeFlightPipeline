from dagster import Definitions, load_assets_from_modules, ScheduleDefinition
from dagster_app.assets import ingestion, silver, gold
from dagster_app.resources.s3_resource import s3_resource
from dagster_app.resources.snowflake_resource import snowflake_resource

ingestion_assets = load_assets_from_modules([ingestion])
silver_assets = load_assets_from_modules([silver])
gold_assets = load_assets_from_modules([gold])

# Define schedules
hourly_etl_schedule = ScheduleDefinition(
    name="hourly_etl",
    cron_schedule="0 * * * *",  # Every hour at minute 0
    job_name="etl_pipeline",
)

# Define all schedules
schedules = [hourly_etl_schedule]

defs = Definitions(
    assets=[*ingestion_assets, *silver_assets, *gold_assets],
    resources={
        "s3": s3_resource,
        "snowflake": snowflake_resource,
    },
    schedules=schedules,
)
