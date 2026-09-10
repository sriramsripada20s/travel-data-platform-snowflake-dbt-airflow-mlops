-- ============================================================================
-- MODEL: dim_experience
-- PURPOSE: One row per bookable experience. Keeps supplier_id as an FK
-- (normalized, matching the star schema diagram) rather than denormalizing
-- supplier attributes onto this table -- join dim_supplier when needed.
-- ============================================================================

with experiences as (
    select * from {{ ref('stg_experiences') }}
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
from experiences
