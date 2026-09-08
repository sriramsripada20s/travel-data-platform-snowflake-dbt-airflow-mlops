with source as (
    select * from {{ source('raw', 'raw_experiences') }}
)

select
    experience_id,
    experience_name,
    city,
    country,
    category,
    supplier_id,
    base_price,
    capacity,
    rating,
    active_flag
from source