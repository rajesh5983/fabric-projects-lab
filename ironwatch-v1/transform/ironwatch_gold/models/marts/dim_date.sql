-- Standard date dimension (DATA_MODEL.md §4), one row per calendar day.
-- Range is derived dynamically from stg_telemetry's actual min/max
-- telemetry_timestamp (confirmed empirically: 2026-03-09 .. 2026-06-06 in
-- the current synthetic snapshot) rather than a hardcoded literal range,
-- so this model stays correct if the synthetic data window changes.
--
-- No recursive CTE (Fabric Warehouse support for it is inconsistent) --
-- the date spine is built from a 1000-row tally table (10x10x10 digit
-- cross join), comfortably covering any date range this project's
-- synthetic data generator produces (SYNTHETIC_DAYS default: 90).
with bounds as (
    select
        cast(min(telemetry_timestamp) as date) as min_date,
        cast(max(telemetry_timestamp) as date) as max_date
    from {{ ref('stg_telemetry') }}
),
digits as (
    select 0 as d union all select 1 union all select 2 union all select 3 union all select 4
    union all select 5 union all select 6 union all select 7 union all select 8 union all select 9
),
tally as (
    select d1.d + (d2.d * 10) + (d3.d * 100) as n
    from digits d1
    cross join digits d2
    cross join digits d3
),
date_spine as (
    select dateadd(day, t.n, b.min_date) as full_date
    from tally t
    cross join bounds b
    where t.n <= datediff(day, b.min_date, b.max_date)
)
select
    cast(convert(varchar(8), full_date, 112) as int) as date_key,
    full_date,
    year(full_date)                                   as [year],
    month(full_date)                                   as [month],
    cast(datename(month, full_date) as varchar(20))    as month_name,
    datepart(quarter, full_date)                        as [quarter],
    day(full_date)                                      as day_of_month,
    cast(datename(weekday, full_date) as varchar(20))   as day_name,
    case when cast(datename(weekday, full_date) as varchar(20)) in ('Saturday', 'Sunday')
         then 1 else 0 end                              as is_weekend
from date_spine
