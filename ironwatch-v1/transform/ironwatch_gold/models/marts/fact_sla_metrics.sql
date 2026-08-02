-- SLA metrics fact. No contract existed anywhere in DATA_MODEL.md prior
-- to this pass (confirmed by direct search -- ARCHITECTURE.md/ADR-001
-- only use "SLA" as a generic label, never a formula or column list) --
-- this is a fresh, minimal, real-data-backed definition, one row per
-- asset:
--
--   uptime_pct = 100 * (1 - SUM(stg_service_history.downtime_hours)
--                            / window_hours)
--     window_hours = the full stg_telemetry min..max timestamp span,
--     the same window for every asset (a uniform 90-day simulation, not
--     per-asset operational calendars).
--   avg_fault_resolution_hours = AVG(DATEDIFF(hour, fault_ts, cleared_ts))
--     over stg_fault_events rows that have actually been cleared
--     (cleared_ts IS NOT NULL) for that asset. NULL for an asset with no
--     cleared faults yet -- there's nothing to average.
--   open_fault_count = int_iw_fault_aggregations.active_fault_count,
--     carried through for context alongside the two metrics above.

with telemetry_window as (
    select
        datediff(hour, min(telemetry_timestamp), max(telemetry_timestamp)) as window_hours
    from {{ ref('stg_telemetry') }}
),

downtime as (
    select
        asset_id,
        sum(downtime_hours) as total_downtime_hours
    from {{ ref('stg_service_history') }}
    group by asset_id
),

fault_resolution as (
    select
        asset_id,
        avg(cast(datediff(hour, fault_ts, cleared_ts) as float)) as avg_fault_resolution_hours
    from {{ ref('stg_fault_events') }}
    where cleared_ts is not null
    group by asset_id
)

select
    convert(bigint, hashbytes('MD5', eq.asset_id)) as asset_key,
    eq.asset_id,
    cast(
        100.0 * (1.0 - (coalesce(dt.total_downtime_hours, 0.0) / tw.window_hours))
        as float
    ) as uptime_pct,
    fr.avg_fault_resolution_hours,
    coalesce(fa.active_fault_count, 0) as open_fault_count,
    cast(getutcdate() as datetime2(6)) as _loaded_utc
from {{ ref('stg_equipment') }} eq
cross join telemetry_window tw
left join downtime dt on eq.asset_id = dt.asset_id
left join fault_resolution fr on eq.asset_id = fr.asset_id
left join {{ ref('int_iw_fault_aggregations') }} fa on eq.asset_id = fa.asset_id
