-- ============================================================================
-- MODEL: dim_date
-- PURPOSE: One row per calendar day. date_day is the primary/join key --
-- kept as an actual DATE rather than a surrogate integer.
-- ============================================================================
-- Date range matches Phase 1's config.py START_DATE/END_DATE. Keep both in
-- sync manually if that window ever changes.
with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="to_date('2025-05-01')",
        end_date="to_date('2028-01-01')"
    ) }}
)

select
    cast(date_day as date) as date_day,
    year(date_day) as year,
    month(date_day) as month,
    day(date_day) as day_of_month,
    dayofweek(date_day) as day_of_week,
    dayname(date_day) as day_name,
    monthname(date_day) as month_name,
    quarter(date_day) as quarter,
    weekofyear(date_day) as week_of_year,
    case when dayofweek(date_day) in (0, 6) then true else false end as is_weekend
from date_spine