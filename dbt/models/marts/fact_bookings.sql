-- ============================================================================
-- MODEL: fact_bookings
-- PURPOSE: One row per booking. Built from int_booking_details, so the ~51
-- orphaned-FK bookings are already excluded.
-- ============================================================================

with bookings as (
    select * from {{ ref('int_booking_details') }}
)

select
    booking_id,
    customer_id,
    experience_id,
    supplier_id,
    cast(experience_date as date) as date_day,

    booking_timestamp,
    number_of_guests,
    ticket_price,
    discount_amount,
    booking_amount,
    lead_time_days,
    discount_pct,

    booking_status,
    payment_status,
    booking_channel,
    currency

from bookings
