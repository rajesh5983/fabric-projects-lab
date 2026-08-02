-- Light staging pass over Bronze service_history_raw (FleetCare). Column
-- rename and type casts only -- no joins, no business logic (see marts/
-- for that). Built to unblock fact_health_score's days_since_service term
-- (ADR-008) -- see docs/ADR/OPEN_DECISIONS.md OPEN-003 for what this
-- model does not yet cover (oil-sample verdict is a separate, unbuilt
-- source).
select
    cast(work_order_id as varchar(50))  as work_order_id,
    cast(asset_id as varchar(50))       as asset_id,
    cast(service_date as date)          as service_date,
    cast(technician_id as varchar(50))  as technician_id,
    cast(service_type as varchar(20))   as service_type,
    cast(parts_used as varchar(500))    as parts_used,
    cast(downtime_hours as float)       as downtime_hours
from {{ source('bronze', 'service_history_raw') }}
