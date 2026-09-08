-- ============================================================================
-- MODEL: stg_bookings
-- PURPOSE: Remove duplicate booking rows from the raw landing table.
-- ============================================================================
-- NOTE: We only fix structural duplicates here (the 202 exact duplicates 
-- generated in Phase 1). 
--
-- We deliberately DO NOT fix bad data values here (like missing customer IDs, 
-- negative prices, or bad experience IDs). Those business errors pass through 
-- so our dbt tests can catch and report them later!
-- ============================================================================

-- STEP 1: Pull all raw records from our Snowflake landing table
with source as (
    select * from {{ source('raw', 'raw_bookings') }}
),

-- STEP 2: Find and keep only 1 copy of each booking_id
deduplicated as (
    select *
    from source
    -- Number each booking row per booking_id. 
    -- If booking_id "B100" appears twice, row 1 is kept and row 2 is dropped.
    qualify row_number() over (
        partition by booking_id
        order by booking_timestamp
    ) = 1
)

-- STEP 3: Select and clean up our final column list
select
    booking_id,
    customer_id,
    experience_id,
    booking_timestamp,
    experience_date,
    number_of_guests,
    ticket_price,
    discount_amount,
    booking_amount,
    booking_channel,
    currency,
    lead_time_days,
    discount_pct,
    booking_status,
    payment_status
from deduplicated