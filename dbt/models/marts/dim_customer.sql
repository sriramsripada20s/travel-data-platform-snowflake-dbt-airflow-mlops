-- ============================================================================
-- MODEL: dim_customer
-- PURPOSE: One row per customer -- descriptive attributes only. Activity
-- metrics (booking counts, LTV) live in int_customer_activity / analytics
-- marts, not here -- dimensions stay descriptive, not aggregated.
-- ============================================================================

with customers as (
    select * from {{ ref('stg_customers') }}
)

select
    customer_id,
    signup_date,
    country,
    preferred_language,
    acquisition_channel,
    customer_segment,
    datediff('day', signup_date, current_date()) as tenure_days
from customers