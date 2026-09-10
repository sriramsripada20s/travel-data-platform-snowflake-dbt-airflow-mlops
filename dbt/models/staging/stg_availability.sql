with source as (
    select * from {{ source('raw', 'raw_availability') }}
)

select
    experience_id,
    experience_date,
    time_slot,
    total_capacity,
    available_capacity,
    price
from source
