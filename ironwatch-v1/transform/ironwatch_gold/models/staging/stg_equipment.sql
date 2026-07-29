-- Light staging pass over Bronze asset_master_raw (asset registry). Column
-- rename and type casts only -- no joins, no business logic (see marts/
-- for that). commission_date is cast here since Bronze stores it as a
-- string, not a native date type.
select
    cast(asset_id as varchar(50))         as asset_id,
    cast(equipment_line as varchar(20))   as equipment_line,
    cast([model] as varchar(50))          as model,
    cast(site as varchar(50))             as site,
    cast(commission_date as date)         as commission_date,
    cast(status as varchar(20))           as status
from {{ source('bronze', 'asset_master_raw') }}
