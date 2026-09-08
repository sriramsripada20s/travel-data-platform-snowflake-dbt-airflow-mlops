-- ============================================================================
-- MODEL: int_booking_details
-- PURPOSE: Enriches clean bookings with full experience and supplier metadata.
-- ============================================================================
-- DATA QUALITY GUARDRAIL:
-- Uses an INNER JOIN against `stg_experiences`. This explicitly excludes the 51 
-- orphaned-FK bookings generated in Phase 1. 
--
-- Those 51 bad rows are captured separately in `int_orphaned_bookings.sql` to 
-- maintain 100% financial auditability without corrupting downstream joins.
-- ============================================================================

-- STEP 1: Pull deduplicated staging bookings
with bookings as (
    select * from {{ ref('stg_bookings') }}
),

-- STEP 2: Pull staging experience catalog
experiences as (
    select * from {{ ref('stg_experiences') }}
),

-- STEP 3: Pull staging supplier details
suppliers as (
    select * from {{ ref('stg_suppliers') }}
),

-- STEP 4: Join bookings -> experiences -> suppliers
enriched_bookings as (
    select
        -- Booking Keys & Timestamps
        b.booking_id,
        b.customer_id,
        b.experience_id,
        b.booking_timestamp,
        b.experience_date,
        
        -- Transaction & Pricing Attributes
        b.number_of_guests,
        b.ticket_price,
        b.discount_amount,
        b.booking_amount,
        b.booking_channel,
        b.currency,
        
        -- Business Rules & ML Feature Inputs
        b.lead_time_days,
        b.discount_pct,
        b.booking_status,
        b.payment_status,

        -- Joined Experience Catalog Metadata
        e.experience_name,
        e.city as experience_city,
        e.country as experience_country,
        e.category as experience_category,
        e.base_price as experience_base_price,
        e.capacity as experience_capacity,

        -- Joined Supplier Metadata
        s.supplier_id,
        s.supplier_name,
        s.supplier_type,
        s.commission_rate

    from bookings b
    -- INNER JOIN ensures only bookings matching valid experience catalog items flow through
    inner join experiences e 
        on b.experience_id = e.experience_id
    -- INNER JOIN links experiences to their contract supplier
    inner join suppliers s 
        on e.supplier_id = s.supplier_id
)

-- STEP 5: Output enriched dataset for downstream marts and aggregations
select * from enriched_bookings