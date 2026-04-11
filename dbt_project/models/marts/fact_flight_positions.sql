{{ config(
    materialized='incremental',
    unique_key='position_id'
) }}

with flights as (
    select * from {{ ref('stg_flights') }}
    {% if is_incremental() %}
      -- this filter will only be applied on an incremental run
      where processed_at > (select max(processed_at) from {{ this }})
    {% endif %}
)

select
    {{ dbt_utils.generate_surrogate_key(['icao24', 'time_position']) }} as position_id,
    icao24 as aircraft_id,
    regexp_substr(callsign, '^[A-Z]{3}') as airline_id,
    callsign,
    time_position as event_time,
    latitude,
    longitude,
    baro_altitude,
    velocity,
    processed_at,
    partition_date
from flights
where time_position is not null
