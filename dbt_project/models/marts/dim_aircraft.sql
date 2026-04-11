{{ config(materialized='table') }}

with flights as (
    select * from {{ ref('stg_flights') }}
),

ranked_aircraft as (
    select
        icao24,
        origin_country,
        max(partition_date) as last_seen_date,
        row_number() over (partition by icao24 order by partition_date desc) as rn
    from flights
    group by icao24, origin_country, partition_date
)

select
    icao24 as aircraft_id,
    origin_country,
    last_seen_date
from ranked_aircraft
where rn = 1
