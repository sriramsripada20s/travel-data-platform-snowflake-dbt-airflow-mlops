-- ============================================================================
-- MODEL: int_experience_daily_metrics
-- PURPOSE: One row per experience + date, summarizing demand and utilization.
-- ============================================================================
-- DATA INTEGRITY NOTE:
-- Built from `int_booking_details` (not `stg_bookings`). The 51 orphaned-FK 
-- bookings are already excluded here, ensuring revenue and booking counts 
-- strictly match our valid experience catalog.
-- ============================================================================

-- STEP 1: Pull clean, enriched bookings
with bookings as (
    select * from {{ ref('int_booking_details') }}
),

-- STEP 2: Pull inventory capacity and slot availability
availability as (
    select * from {{ ref('stg_availability') }}
),

-- STEP 3: Pull experience catalog metadata (names, cities, categories)
experiences as (
    select * from {{ ref('stg_experiences') }}
),

-- STEP 4: Aggregate inventory capacity to (experience_id, date) grain
daily_availability as (
    select
        experience_id,
        experience_date,
        sum(total_capacity) as total_capacity,
        sum(available_capacity) as available_capacity
    from availability
    group by experience_id, experience_date
),

-- STEP 5: Aggregate booking activity to (experience_id, date) grain
daily_bookings as (
    select
        experience_id,
        experience_date,
        count(*) as total_bookings,
        count_if(booking_status = 'CONFIRMED') as confirmed_bookings,
        count_if(booking_status = 'CANCELLED') as cancelled_bookings,
        count_if(booking_status = 'REFUNDED') as refunded_bookings,
        sum(number_of_guests) as total_guests,
        sum(booking_amount) as total_booking_amount,
        sum(case when booking_status = 'CONFIRMED' then booking_amount else 0 end) as confirmed_booking_amount,
        avg(lead_time_days) as avg_lead_time_days
    from bookings
    group by experience_id, experience_date
)

-- STEP 6: Combine experiences, availability, and bookings into daily metrics
select
    -- Experience Identifiers & Attributes
    e.experience_id,
    e.experience_name,
    e.city,
    e.category,
    
    -- Date Dimension (Fall back to availability date if no bookings occurred)
    coalesce(b.experience_date, a.experience_date) as experience_date,
    
    -- Booking Volume Metrics (COALESCE replaces NULL with 0 for quiet days)
    coalesce(b.total_bookings, 0) as total_bookings,
    coalesce(b.confirmed_bookings, 0) as confirmed_bookings,
    coalesce(b.cancelled_bookings, 0) as cancelled_bookings,
    coalesce(b.refunded_bookings, 0) as refunded_bookings,
    coalesce(b.total_guests, 0) as total_guests,
    coalesce(b.total_booking_amount, 0) as total_booking_amount,
    coalesce(b.confirmed_booking_amount, 0) as confirmed_booking_amount,
    b.avg_lead_time_days,
    
    -- Inventory Capacity Metrics
    a.total_capacity,
    a.available_capacity,
    
    -- DERIVED KPI 1: Utilization Rate (Booked Slots / Total Slots)
    case
        when a.total_capacity > 0
            then round((a.total_capacity - a.available_capacity) / a.total_capacity, 4)
        else null
    end as utilization_rate,
    
    -- DERIVED KPI 2: Cancellation Rate (Cancelled Bookings / Total Bookings)
    case
        when coalesce(b.total_bookings, 0) > 0
            then round(coalesce(b.cancelled_bookings, 0) / b.total_bookings, 4)
        else null
    end as cancellation_rate

from experiences e
-- INNER JOIN guarantees every experience row has matching inventory availability
inner join daily_availability a 
    on e.experience_id = a.experience_id
-- LEFT JOIN ensures days with 0 bookings still show up with 0s rather than vanishing
left join daily_bookings b
    on e.experience_id = b.experience_id
    and a.experience_date = b.experience_date