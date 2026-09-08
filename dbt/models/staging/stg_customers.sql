with source as (
    select * from {{ source('raw', 'raw_customers') }}
)

select
    customer_id,
    signup_date,
    country,
    preferred_language,
    acquisition_channel,
    customer_segment
from source