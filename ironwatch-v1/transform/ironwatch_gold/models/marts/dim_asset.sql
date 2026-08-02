-- Asset dimension (DATA_MODEL.md §4). One row per asset, sourced 1:1 from
-- stg_equipment (already unique/not_null on asset_id). asset_key is a
-- surrogate key derived deterministically from the natural key so it's
-- stable across rebuilds without needing an identity/sequence column in a
-- table-materialized model.
select
    cast(convert(bigint, hashbytes('MD5', asset_id)) as bigint) as asset_key,
    asset_id,
    equipment_line,
    [model],
    site,
    commission_date,
    status,
    cast(getutcdate() as datetime2(6)) as _loaded_utc
from {{ ref('stg_equipment') }}
