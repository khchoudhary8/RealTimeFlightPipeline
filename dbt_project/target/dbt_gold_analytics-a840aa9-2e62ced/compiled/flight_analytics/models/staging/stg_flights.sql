with source as (
    select * from FLIGHTS_RAW.RAW.FLIGHTS_RAW
),

renamed as (
    select
        ICAO24 as icao24,
        CALLSIGN as callsign,
        ORIGIN_COUNTRY as origin_country,
        TIME_POSITION as time_position,
        LONGITUDE as longitude,
        LATITUDE as latitude,
        BARO_ALTITUDE as baro_altitude,
        VELOCITY as velocity,
        PROCESSED_AT as processed_at,
        PARTITION_DATE as partition_date
    from source
)

select * from renamed