from dagster import asset, ConfigurableResource
from dagster_snowflake import SnowflakeResource
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas


@asset
def gold_flights(context, silver_flights: pd.DataFrame, snowflake: SnowflakeResource):
    """
    Takes the new flights dataframe from Silver,
    loads it into Snowflake 'flights_raw' table (appending),
    and creates/updates Gold analytical views.
    """
    if silver_flights.empty:
        context.log.info("Skipping Snowflake load: No new records.")
        return

    # Use the context manager to get the connection
    with snowflake.get_connection() as conn:
        cursor = conn.cursor()
        db = snowflake.database
        schema = snowflake.schema

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db}")
        cursor.execute(f"USE DATABASE {db}")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        cursor.execute(f"USE SCHEMA {schema}")

        # Load Data
        context.log.info(f"Loading {len(silver_flights)} rows to Snowflake table FLIGHTS_RAW...")
        success, nchunks, nrows, _ = write_pandas(
            conn,
            silver_flights,
            table_name="FLIGHTS_RAW",
            database=db,
            schema=schema,
            auto_create_table=True,
            overwrite=False,  # Append
        )

        if success:
            context.log.info(f"Successfully loaded {nrows} rows to Snowflake.")
        else:
            raise Exception("Failed to write to Snowflake")

        # Create/Update Gold Views
        create_gold_views(context, cursor)


def create_gold_views(context, cursor):
    """Create analytical views on top of FLIGHTS_RAW table"""

    views = [
        """
        CREATE OR REPLACE VIEW daily_flight_counts AS
        SELECT
            DATE("partition_date") as partition_date,
            "origin_country",
            COUNT(*) as flight_count,
            AVG("baro_altitude") as avg_altitude,
            AVG("velocity") as avg_velocity
        FROM FLIGHTS_RAW
        WHERE "partition_date" IS NOT NULL
        GROUP BY DATE("partition_date"), "origin_country"
        ORDER BY DATE("partition_date") DESC, flight_count DESC;
        """,
        """
        CREATE OR REPLACE VIEW hourly_flight_activity AS
        SELECT
            DATE("partition_date") as partition_date,
            HOUR("time_position") as hour_of_day,
            COUNT(*) as flight_count,
            COUNT(DISTINCT "icao24") as unique_aircraft
        FROM FLIGHTS_RAW
        WHERE "time_position" IS NOT NULL
        GROUP BY DATE("partition_date"), HOUR("time_position")
        ORDER BY DATE("partition_date") DESC, hour_of_day;
        """,
        """
        CREATE OR REPLACE VIEW top_airlines AS
        SELECT
            SUBSTRING("callsign", 1, 3) as airline_code,
            "origin_country",
            COUNT(*) as flight_count,
            AVG("baro_altitude") as avg_altitude,
            AVG("velocity") as avg_velocity
        FROM FLIGHTS_RAW
        WHERE "callsign" IS NOT NULL AND LENGTH("callsign") >= 3
        GROUP BY SUBSTRING("callsign", 1, 3), "origin_country"
        ORDER BY flight_count DESC
        LIMIT 50;
        """,
    ]

    for sql in views:
        try:
            cursor.execute(sql)
            context.log.info(f"Created/updated view: {sql.split()[2]}")
        except Exception as e:
            context.log.error(f"Failed to create view: {e}")
