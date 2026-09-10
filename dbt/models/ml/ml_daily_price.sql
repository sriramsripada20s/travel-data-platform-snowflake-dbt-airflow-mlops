select
    experience_id,
    date_day,
    avg(price) as avg_price
from {{ ref('fact_experience_availability') }}
group by experience_id, date_day
