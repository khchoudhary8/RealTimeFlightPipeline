with flights as (
    select * from FLIGHT_ANALYTICS.RAW_silver.stg_flights
)

select
    partition_date,
    origin_country,
    count(*) as flight_count,
    avg(baro_altitude) as avg_altitude,
    avg(velocity) as avg_velocity
from flights
where time_position is not null
group by partition_date, origin_country