-- Light staging pass over Bronze oil_samples_raw (FluidLab). Column
-- rename and type casts only -- no joins, no business logic (see
-- intermediate/ for the ADR-008 same-calendar-day temporal join, and
-- marts/ for fact_health_score's OilVerdictPenalty term). Built to
-- resolve OPEN-003 (docs/ADR/OPEN_DECISIONS.md).
select
    cast(sample_id as varchar(50))          as sample_id,
    cast(asset_id as varchar(50))           as asset_id,
    cast(sample_date as date)               as sample_date,
    cast(iron_ppm as float)                 as iron_ppm,
    cast(viscosity_cst as float)            as viscosity_cst,
    cast(water_content_pct as float)        as water_content_pct,
    cast(particle_count as int)             as particle_count,
    cast(lab_verdict as varchar(20))        as lab_verdict
from {{ source('bronze', 'oil_samples_raw') }}
