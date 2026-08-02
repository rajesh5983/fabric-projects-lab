-- Telemetry fact (DATA_MODEL.md §4). One row per stg_telemetry reading
-- (15-min cadence, unaggregated), joined to dim_asset/dim_date surrogate
-- keys. asset_key is computed with the same deterministic MD5-hash
-- expression as dim_asset.asset_key so the join key matches without a
-- physical join back to dim_asset for key resolution.
--
-- telemetry_timestamp is re-cast to an explicit datetime2(6) here --
-- stg_telemetry.sql casts it as bare `datetime2` (no precision), which
-- Fabric Warehouse accepts for a view but rejects for a table-materialized
-- CTAS ("An integer precision value between 0 and 6 must be specified").
-- Fixed locally rather than editing stg_telemetry.sql, an already-shipped
-- Silver model outside this PR's scope.
select
    convert(bigint, hashbytes('MD5', t.asset_id))       as asset_key,
    cast(convert(varchar(8), t.telemetry_timestamp, 112) as int) as date_key,
    t.asset_id,
    cast(t.telemetry_timestamp as datetime2(6))         as telemetry_timestamp,
    t.engine_rpm,
    t.coolant_temp_c,
    t.hydraulic_pressure_bar,
    t.vibration_mms,
    t.fuel_rate_lph,
    t.gps_lat,
    t.gps_lon,
    cast(getutcdate() as datetime2(6)) as _loaded_utc
from {{ ref('stg_telemetry') }} t
