with base as (
    select * from {{ ref('ml_base_features') }}
),
daily_metrics as (
    select * from {{ ref('int_experience_daily_metrics') }}
)

select
    b.*,
    lag(dm.total_bookings, 1) over (
        partition by b.experience_id order by b.feature_date
    ) as bookings_prev_1d,
    avg(dm.total_bookings) over (
        partition by b.experience_id order by b.feature_date
        rows between 7 preceding and 1 preceding
    ) as bookings_prev_7d_avg,
    avg(dm.total_bookings) over (
        partition by b.experience_id order by b.feature_date
        rows between 28 preceding and 1 preceding
    ) as bookings_prev_28d_avg,
    avg(dm.utilization_rate) over (
        partition by b.experience_id order by b.feature_date
        rows between 7 preceding and 1 preceding
    ) as utilization_prev_7d_avg,
    avg(dm.cancellation_rate) over (
        partition by b.experience_id order by b.feature_date
        rows between 28 preceding and 1 preceding
    ) as cancellation_rate_prev_28d_avg,
    row_number() over (
        partition by b.experience_id order by b.feature_date
    ) - 1 as days_of_prior_history
from base b
join daily_metrics dm
    on b.experience_id = dm.experience_id
    and b.feature_date = dm.experience_date