from dagster import Definitions, load_assets_from_modules, define_asset_job, ScheduleDefinition, AssetSelection
from orchestration import assets
from orchestration.assets import dbt as dbt_assets_module

# Load standard assets
core_assets = load_assets_from_modules([assets])
# Load dbt assets
dbt_analytics_assets = load_assets_from_modules([dbt_assets_module])

all_assets = [*core_assets, *dbt_analytics_assets]

# Define a job that materializes all assets
flight_pipeline_job = define_asset_job(
    name="flight_pipeline_job",
    selection=AssetSelection.all()
)

# Define a schedule to run the job every 15 minutes
flight_pipeline_schedule = ScheduleDefinition(
    job=flight_pipeline_job,
    cron_schedule="*/15 * * * *",  # Every 15 minutes
)

defs = Definitions(
    assets=all_assets,
    schedules=[flight_pipeline_schedule],
    resources={
        "dbt": dbt_assets_module.dbt_resource,
    },
)
