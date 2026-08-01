-- Light staging pass over Bronze fault_codes_raw (static OX- fault-code
-- catalog: 15 rows, one per fault code). Column rename and type casts
-- only -- no joins, no business logic (see intermediate/ for that).
select
    cast(fault_code as varchar(10))    as fault_code,
    cast(category as varchar(20))      as category,
    cast(description as varchar(100)) as description,
    cast(severity as varchar(10))      as severity
from {{ source('bronze', 'fault_codes_raw') }}
