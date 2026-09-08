with source as (
    select * from {{ source('raw', 'raw_suppliers') }}
)

select
    supplier_id,
    supplier_name,
    country,
    supplier_type,
    contract_start_date,
    commission_rate,
    supplier_status
from source