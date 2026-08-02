-- health_score must fall within the range the formula defines (0-100,
-- clamped by construction in the model SQL). Singular dbt test: fails if
-- this query returns any rows.
select
    asset_id,
    health_score
from {{ ref('fact_health_score') }}
where health_score < 0
   or health_score > 100
