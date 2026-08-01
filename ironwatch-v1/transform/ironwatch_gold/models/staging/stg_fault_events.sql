-- Light staging pass over Bronze fault_events_raw (per-asset fault-event
-- stream, derived from telemetry anomalies -- see generate_fault_events()
-- in synthetic_data/generators/generate_all.py and docs/ADR/OPEN_DECISIONS.md
-- OPEN-002). Column rename and type casts only -- no joins, no aggregation
-- (see intermediate/ for that).
select
    cast(asset_id as varchar(50))    as asset_id,
    cast(fault_code as varchar(10))  as fault_code,
    cast(fault_ts as datetime2)      as fault_ts,
    cast(active_flag as bit)         as active_flag,
    cast(cleared_ts as datetime2)    as cleared_ts
from {{ source('bronze', 'fault_events_raw') }}
