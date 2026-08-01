-- Fault-event enrichment and per-asset aggregation layer. Enrichment
-- (joining fault events to equipment and to the fault-code catalog)
-- belongs here, not staging, per the earlier decision -- resolves the
-- join/aggregation scope of OPEN-002 (docs/ADR/OPEN_DECISIONS.md).
--
-- hours_operated not-negative check: NOT applied. Re-confirmed directly
-- against docs/ADR/ADR-008-utilization-and-health-score-redesign.md before
-- writing this model (Status: Accepted, 2026-06-20) -- hours_operated does
-- not exist on any Bronze source, and Option B (reintroducing it) was
-- explicitly rejected in favor of calendar-time-based logic elsewhere in
-- the data model. There is no field to check against here; this is a
-- confirmed absence, not a silently-omitted check.

with fault_events_enriched as (

    select
        fe.asset_id,
        fe.fault_code,
        fe.fault_ts,
        fe.active_flag,
        fe.cleared_ts,
        fc.category,
        fc.description,
        fc.severity
    from {{ ref('stg_fault_events') }} fe
    left join {{ ref('stg_fault_codes') }} fc
        on fe.fault_code = fc.fault_code

),

most_recent_fault as (

    -- Two different anomaly types can start a qualifying run at the exact
    -- same 15-min reading for the same asset (independent draws over the
    -- same timestamp series), which would tie on fault_ts. No sequence/
    -- ingestion-order column exists on fault_events_raw to break that tie,
    -- so fault_code (alphabetical) is used as an explicit, deterministic --
    -- if arbitrary -- secondary key. Without it, ROW_NUMBER() has no
    -- guaranteed stable order across ties and this view's "most recent
    -- fault" columns could flip between runs.
    select
        asset_id,
        fault_code,
        fault_ts,
        category,
        severity,
        row_number() over (
            partition by asset_id
            order by fault_ts desc, fault_code asc
        ) as rn
    from fault_events_enriched

),

fault_aggregates as (

    select
        asset_id,
        count(*)                                          as total_fault_count,
        sum(case when active_flag = 1 then 1 else 0 end)  as active_fault_count,
        count(distinct fault_code)                        as distinct_fault_code_count
    from fault_events_enriched
    group by asset_id

)

select
    eq.asset_id,
    eq.equipment_line,
    eq.site,
    coalesce(fa.total_fault_count, 0)          as total_fault_count,
    coalesce(fa.active_fault_count, 0)         as active_fault_count,
    coalesce(fa.distinct_fault_code_count, 0)  as distinct_fault_code_count,
    mrf.fault_ts                               as most_recent_fault_ts,
    mrf.fault_code                             as most_recent_fault_code,
    mrf.category                               as most_recent_fault_category,
    mrf.severity                               as most_recent_fault_severity
from {{ ref('stg_equipment') }} eq
left join fault_aggregates fa
    on eq.asset_id = fa.asset_id
left join most_recent_fault mrf
    on eq.asset_id = mrf.asset_id
    and mrf.rn = 1
