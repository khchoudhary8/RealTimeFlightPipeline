{{ config(materialized='table') }}

with flights as (
    select * from {{ ref('stg_flights') }}
),

-- Extract the 3-letter ICAO Airline code from the callsign (e.g., UAL123 -> UAL)
extracted_airlines as (
    select
        regexp_substr(callsign, '^[A-Z]{3}') as airline_code
    from flights
    where callsign is not null
    and regexp_substr(callsign, '^[A-Z]{3}') is not null
)

select
    airline_code as airline_id,
    count(*) as total_historical_waypoints  
    -- In a real enterprise system, we would join this against a static seeds.csv of 
    -- actual airline names (e.g., UAL -> United Airlines).
from extracted_airlines
group by airline_code
