
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject
from pathlib import Path

# Point to dbt project directory
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent.joinpath("dbt_project")

dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
)

dbt_resource = DbtCliResource(project_dir=dbt_project)

@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_gold_analytics(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
