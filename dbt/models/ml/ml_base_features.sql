with daily_metrics as (
    select * from {{ ref('int_experience_daily_metrics') }}
),
experiences as (
    select * from {{ ref('dim_experience') }}
),
dates as (
    select * from {{ ref('dim_date') }}
),
daily_price as (
    select * from {{ ref('ml_daily_price') }}
)

select
    dm.experience_id,
    dm.experience_date as feature_date,
    d.day_of_week,
    d.is_weekend,
    d.month,
    d.quarter,
    d.day_name,
    e.city,
    e.category,
    e.capacity,
    e.rating,
    e.base_price,
    dp.avg_price,
    dm.total_bookings as target_bookings,
    dm.confirmed_bookings as target_confirmed_bookings,
    dm.cancellation_rate as target_cancellation_rate,
    dm.utilization_rate as target_utilization_rate
from daily_metrics dm
join experiences e on dm.experience_id = e.experience_id
join dates d on dm.experience_date = d.date_day
left join daily_price dp
    on dm.experience_id = dp.experience_id
    and dm.experience_date = dp.date_day