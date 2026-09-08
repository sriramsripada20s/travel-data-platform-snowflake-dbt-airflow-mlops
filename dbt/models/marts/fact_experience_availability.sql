-- ============================================================================
-- MODEL: fact_experience_availability
-- PURPOSE: One row per experience + date + timeslot -- inventory snapshot.
-- ============================================================================

with availability as (
    select * from {{ ref('stg_availability') }}
)

select
    experience_id,
    cast(experience_date as date) as date_day,
    time_slot,
    total_capacity,
    available_capacity,
    price,
    case
        when total_capacity > 0
            then round((total_capacity - available_capacity) / total_capacity, 4)
        else null
    end as utilization_rate
from availability