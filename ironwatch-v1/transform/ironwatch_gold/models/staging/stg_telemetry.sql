-- Light staging pass over Bronze telemetry_raw (PulseNet). Column rename
-- and type casts only -- no joins, no business logic (see marts/ for that).
select
    cast(asset_id as varchar(50))          as asset_id,
    cast([timestamp] as datetime2)         as telemetry_timestamp,
    cast(engine_rpm as int)                as engine_rpm,
    cast(coolant_temp_c as float)          as coolant_temp_c,
    cast(hydraulic_pressure_bar as float)  as hydraulic_pressure_bar,
    cast(vibration_mms as float)           as vibration_mms,
    cast(fuel_rate_lph as float)           as fuel_rate_lph,
    cast(gps_lat as float)                 as gps_lat,
    cast(gps_lon as float)                 as gps_lon
from {{ source('bronze', 'telemetry_raw') }}
