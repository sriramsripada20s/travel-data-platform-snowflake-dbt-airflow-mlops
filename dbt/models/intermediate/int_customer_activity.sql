-- ============================================================================
-- MODEL: int_customer_activity
-- PURPOSE: One row per customer summarizing lifetime bookings and app activity.
-- ============================================================================
-- DATA INTEGRITY NOTE:
-- We build this from `int_booking_details` (not `stg_bookings`). This ensures
-- that a customer's booking stats only count valid bookings that matched a 
-- real experience, keeping our metrics 100% clean.
-- ============================================================================

-- STEP 1: Pull our base list of customer profiles
with customers as (
    select * from {{ ref('stg_customers') }}
),

-- STEP 2: Pull clean, enriched booking records
bookings as (
    select * from {{ ref('int_booking_details') }}
),

-- STEP 3: Pull web and app event clickstream logs
web_events as (
    select * from {{ ref('stg_web_events') }}
),

-- STEP 4: Aggregate booking stats per customer
booking_agg as (
    select
        customer_id,
        count(*) as total_bookings,
        
        -- Status counts
        count_if(booking_status = 'CONFIRMED') as confirmed_bookings,
        count_if(booking_status = 'CANCELLED') as cancelled_bookings,
        count_if(booking_status = 'REFUNDED') as refunded_bookings,
        
        -- Lifetime Value (LTV) metrics
        sum(booking_amount) as lifetime_booking_amount,
        sum(case when booking_status = 'CONFIRMED' then booking_amount else 0 end) as lifetime_confirmed_amount,
        
        -- First and most recent booking timestamps
        min(booking_timestamp) as first_booking_at,
        max(booking_timestamp) as last_booking_at
        
    from bookings
    -- Exclude missing customer IDs (~101 raw rows) so we don't group bad rows together
    where customer_id is not null
    group by customer_id
),

-- STEP 5: Aggregate web and app session stats per customer
session_agg as (
    select
        customer_id,
        count(distinct session_id) as total_sessions,
        count_if(event_type = 'SEARCH') as search_events,
        count_if(event_type = 'PURCHASE') as purchase_events,
        min(event_timestamp) as first_event_at,
        max(event_timestamp) as last_event_at
    from web_events
    group by customer_id
)

-- STEP 6: Join everything back to the main customer profile
select
    -- Core Customer Attributes
    c.customer_id,
    c.signup_date,
    c.country,
    c.acquisition_channel,
    c.customer_segment,
    
    -- Booking Summaries (COALESCE replaces NULL with 0 for customers with 0 bookings)
    coalesce(b.total_bookings, 0) as total_bookings,
    coalesce(b.confirmed_bookings, 0) as confirmed_bookings,
    coalesce(b.cancelled_bookings, 0) as cancelled_bookings,
    coalesce(b.refunded_bookings, 0) as refunded_bookings,
    coalesce(b.lifetime_booking_amount, 0) as lifetime_booking_amount,
    coalesce(b.lifetime_confirmed_amount, 0) as lifetime_confirmed_amount,
    b.first_booking_at,
    b.last_booking_at,
    
    -- Web Behavior Summaries (COALESCE replaces NULL with 0 for users with 0 events)
    coalesce(s.total_sessions, 0) as total_sessions,
    coalesce(s.search_events, 0) as search_events,
    coalesce(s.purchase_events, 0) as purchase_events,
    s.first_event_at,
    s.last_event_at,
    
    -- Derived Business Flag: TRUE if the customer has made more than 1 booking
    case when coalesce(b.total_bookings, 0) > 1 then true else false end as is_repeat_booker

from customers c
-- LEFT JOIN ensures customers who signed up but haven't booked/browsed are still kept
left join booking_agg b on c.customer_id = b.customer_id
left join session_agg s on c.customer_id = s.customer_id