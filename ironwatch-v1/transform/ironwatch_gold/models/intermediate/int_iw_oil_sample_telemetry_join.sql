-- Oil-sample <-> telemetry same-calendar-day temporal join, per ADR-008
-- Sec3 (docs/ADR/ADR-008-utilization-and-health-score-redesign.md) --
-- resolves the oil-side half of OPEN-003
-- (docs/ADR/OPEN_DECISIONS.md). This is the real Silver DQ-rule-2.2.5
-- join design (previously documented but not built -- see DATA_MODEL.md
-- Sec2.2/Sec3), attaching telemetry operating context to each oil sample
-- taken on the same calendar day, NOT a join to fault_events (ADR-008
-- never describes an oil-sample<->fault-event join).
--
-- Matching logic (ADR-008 Sec3):
--   1. For a given oil sample, gather all stg_telemetry rows for the
--      same asset_id where CAST(telemetry_timestamp AS DATE) = sample_date.
--   2. If at least one candidate row exists, select the reading closest
--      to local midday (there is no timezone concept anywhere in this
--      dataset -- all timestamps are UTC per DATA_MODEL.md Sec1.1 -- so
--      "local midday" is taken as 12:00 UTC on sample_date) as a
--      representative point for that day's operating context.
--   3. If no telemetry row exists for that asset on that date, the oil
--      sample has no match and is dropped (per Silver DQ rule 2.2.5 --
--      this intermediate model reproduces that same drop behavior via
--      an inner join).

with candidates as (
    select
        os.sample_id,
        os.asset_id,
        os.sample_date,
        os.lab_verdict,
        os.iron_ppm,
        os.viscosity_cst,
        os.water_content_pct,
        os.particle_count,
        t.telemetry_timestamp,
        t.coolant_temp_c,
        t.hydraulic_pressure_bar,
        t.vibration_mms,
        t.fuel_rate_lph,
        row_number() over (
            partition by os.sample_id
            order by abs(datediff(
                minute,
                t.telemetry_timestamp,
                dateadd(hour, 12, cast(os.sample_date as datetime2(0)))
            )) asc
        ) as rn
    from {{ ref('stg_oil_samples') }} os
    inner join {{ ref('stg_telemetry') }} t
        on os.asset_id = t.asset_id
        and cast(t.telemetry_timestamp as date) = os.sample_date
)

select
    sample_id,
    asset_id,
    sample_date,
    lab_verdict,
    iron_ppm,
    viscosity_cst,
    water_content_pct,
    particle_count,
    telemetry_timestamp as matched_telemetry_timestamp,
    coolant_temp_c,
    hydraulic_pressure_bar,
    vibration_mms,
    fuel_rate_lph
from candidates
where rn = 1
