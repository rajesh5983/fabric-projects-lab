-- Health score fact (DATA_MODEL.md §5 / ADR-008). One row per asset
-- (current-state snapshot, not per-hour -- see fact_health_score.yml for
-- why the aspirational per-asset-per-hour grain in DATA_MODEL.md §4 isn't
-- achievable from the Silver models built so far).
--
-- FORMULA (all 3 documented terms -- resolves OPEN-003,
-- docs/ADR/OPEN_DECISIONS.md):
--   HealthScore = 100
--     - (active_fault_count * FaultPenalty(most_recent_fault_severity))
--     - OilVerdictPenalty(most_recent_oil_verdict)
--     - (pct_through_service_window * 20)
--   FaultPenalty:       LOW=2  MEDIUM=5  HIGH=10  CRITICAL=20
--   OilVerdictPenalty:  Normal=0  Watch=10  Critical=25
--   pct_through_service_window = min(days_since_service / 30.0, 1.0)
--     (1.0 -- i.e. max penalty -- when the asset has no service_history
--     row at all)
--   Bands: >=80 Healthy | 60-79 Watch | 40-59 Warning | <40 Critical
--
-- FaultPenalty note: int_iw_fault_aggregations exposes only the single
-- most-recent fault's severity, not a per-event severity breakdown of
-- every currently-active fault. active_fault_count * FaultPenalty(
-- most_recent_fault_severity) is mathematically exact whenever
-- active_fault_count <= 1 -- true for every asset in the current
-- synthetic snapshot (OPEN-002: only 3 assets carry a single
-- deterministically-reopened active fault each; all others have 0). A
-- true per-severity summation would require joining stg_fault_events
-- directly instead of the aggregation -- not done here, to match the
-- task's specified source (int_iw_fault_aggregations).
--
-- OilVerdictPenalty note: sourced from
-- int_iw_oil_sample_telemetry_join (the ADR-008 Sec3 same-calendar-day
-- match, NOT the raw stg_oil_samples staging table -- DATA_MODEL.md
-- Sec5 says "from the most recent matched oil sample", and "matched" is
-- specifically what that intermediate model produces). Most recent by
-- sample_date per asset. An asset with no matched oil sample at all
-- (either no oil_samples_raw rows, or no telemetry row on the same
-- calendar day for any of its samples) gets oil_verdict_penalty = 0,
-- not the max -- unlike service-window's "no record = max penalty"
-- convention, a missing oil match reflects a data-availability gap, not
-- an inherent risk signal, so it is not penalized.
--
-- AS_OF_DATE note: this is a frozen synthetic dataset (telemetry ends
-- 2026-06-06), not a live feed. Using literal CURRENT_DATE for
-- days_since_service would pin every asset's service-window penalty at
-- its -20 max as of today's real wall-clock date (and grow "worse" every
-- day this model is rerun, despite the underlying data never changing) --
-- a deliberate, confirmed departure from ADR-008's literal wording.
-- AS_OF_DATE instead anchors to MAX(telemetry_timestamp), treating the
-- synthetic window's own end as "now" for this formula.
--
-- reference_cadence_days = 30, matching DATA_MODEL.md §5's worked example
-- exactly (flat, not per-service_type -- ADR-008 leaves that unfixed).

with as_of as (
    select cast(max(telemetry_timestamp) as date) as as_of_date
    from {{ ref('stg_telemetry') }}
),

service_recency as (
    select
        asset_id,
        max(service_date) as last_service_date
    from {{ ref('stg_service_history') }}
    group by asset_id
),

service_window as (
    select
        eq.asset_id,
        sr.last_service_date,
        datediff(day, sr.last_service_date, ao.as_of_date) as days_since_service
    from {{ ref('stg_equipment') }} eq
    cross join as_of ao
    left join service_recency sr on eq.asset_id = sr.asset_id
),

service_window_scored as (
    select
        asset_id,
        last_service_date,
        days_since_service,
        case
            when last_service_date is null then 1.0
            when cast(days_since_service as float) / 30.0 > 1.0 then 1.0
            else cast(days_since_service as float) / 30.0
        end as pct_through_service_window
    from service_window
),

fault_penalty as (
    select
        asset_id,
        active_fault_count,
        most_recent_fault_severity,
        case
            when active_fault_count = 0 then 0
            else active_fault_count * case most_recent_fault_severity
                when 'LOW' then 2
                when 'MEDIUM' then 5
                when 'HIGH' then 10
                when 'CRITICAL' then 20
                else 0
            end
        end as fault_penalty
    from {{ ref('int_iw_fault_aggregations') }}
),

oil_verdict_recency as (
    select
        asset_id,
        sample_date,
        lab_verdict,
        row_number() over (
            partition by asset_id
            order by sample_date desc
        ) as rn
    from {{ ref('int_iw_oil_sample_telemetry_join') }}
),

oil_penalty as (
    select
        asset_id,
        sample_date as last_oil_sample_date,
        lab_verdict as most_recent_oil_verdict,
        case lab_verdict
            when 'Normal' then 0
            when 'Watch' then 10
            when 'Critical' then 25
            else 0
        end as oil_verdict_penalty
    from oil_verdict_recency
    where rn = 1
),

scored as (
    select
        eq.asset_id,
        fp.active_fault_count,
        fp.most_recent_fault_severity,
        fp.fault_penalty,
        op.last_oil_sample_date,
        op.most_recent_oil_verdict,
        coalesce(op.oil_verdict_penalty, 0)               as oil_verdict_penalty,
        sw.last_service_date,
        sw.days_since_service,
        sw.pct_through_service_window,
        cast(sw.pct_through_service_window * 20 as float) as service_window_penalty
    from {{ ref('stg_equipment') }} eq
    left join fault_penalty fp on eq.asset_id = fp.asset_id
    left join oil_penalty op on eq.asset_id = op.asset_id
    left join service_window_scored sw on eq.asset_id = sw.asset_id
),

-- Defensive clamp to [0, 100]: penalties are always >= 0 here, so the
-- raw score can't exceed 100, but a floor at 0 guards against a
-- multi-active-fault asset (active_fault_count > 1, none exist in the
-- current synthetic snapshot -- see the FaultPenalty note above) driving
-- the raw score negative. Keeps the health_score-in-range test an actual
-- guarantee, not just a coincidence of today's data.
clamped as (
    select
        *,
        case
            when (100 - fault_penalty - oil_verdict_penalty - service_window_penalty) > 100 then 100
            when (100 - fault_penalty - oil_verdict_penalty - service_window_penalty) < 0 then 0
            else (100 - fault_penalty - oil_verdict_penalty - service_window_penalty)
        end as health_score
    from scored
)

select
    convert(bigint, hashbytes('MD5', c.asset_id))                    as asset_key,
    (select cast(convert(varchar(8), as_of_date, 112) as int) from as_of) as date_key,
    c.asset_id,
    c.active_fault_count,
    c.most_recent_fault_severity,
    c.fault_penalty,
    c.last_oil_sample_date,
    c.most_recent_oil_verdict,
    c.oil_verdict_penalty,
    c.last_service_date,
    c.days_since_service,
    c.pct_through_service_window,
    c.service_window_penalty,
    c.health_score,
    case
        when c.health_score >= 80 then 'Healthy'
        when c.health_score >= 60 then 'Watch'
        when c.health_score >= 40 then 'Warning'
        else 'Critical'
    end                                                                as health_band,
    cast(getutcdate() as datetime2(6))                                as _loaded_utc
from clamped c
