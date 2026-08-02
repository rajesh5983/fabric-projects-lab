-- active_fault_count must never be negative and must never exceed
-- total_fault_count for the same asset. Singular dbt test: fails if this
-- query returns any rows.
select
    asset_id,
    active_fault_count,
    total_fault_count
from {{ ref('int_iw_fault_aggregations') }}
where active_fault_count < 0
   or active_fault_count > total_fault_count
