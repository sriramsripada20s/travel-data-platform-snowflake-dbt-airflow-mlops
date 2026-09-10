{{ config(materialized='table') }}

select
    experience_id,
    feature_date,
    day_of_week,
    is_weekend,
    month,
    quarter,
    day_name,
    city,
    category,
    capacity,
    rating,
    base_price,
    avg_price,
    bookings_prev_1d,
    bookings_prev_7d_avg,
    bookings_prev_28d_avg,
    utilization_prev_7d_avg,
    cancellation_rate_prev_28d_avg,
    days_of_prior_history,
    target_bookings,
    target_confirmed_bookings,
    target_cancellation_rate,
    target_utilization_rate
from {{ ref('ml_rolling_features') }}
