-- ============================================================================
-- MODEL: stg_web_events
-- PURPOSE: Remove duplicate web/app event rows from the raw landing table.
-- ============================================================================
-- NOTE: We only fix structural duplicates here (the 2,997 duplicate event IDs 
-- generated in Phase 1). 
--
-- We deliberately DO NOT fix out-of-order event timestamps within a session.
-- Those behavioral defects pass through so downstream dbt tests can catch 
-- and report them instead of silently modifying raw user behavior.
-- ============================================================================

-- STEP 1: Pull all raw records from our Snowflake landing table
with source as (
    select * from {{ source('raw', 'raw_web_events') }}
),

-- STEP 2: Keep only 1 copy of each event_id
deduplicated as (
    select *
    from source
    -- Number each event row per event_id. 
    -- If event_id "EVT_99" appears twice, row 1 is kept and row 2 is dropped.
    qualify row_number() over (
        partition by event_id
        order by event_timestamp
    ) = 1
)

-- STEP 3: Output standard event columns for downstream funnel analytics
select
    event_id,
    customer_id,
    session_id,
    experience_id,
    event_timestamp,
    event_type,
    device_type,
    traffic_source,
    city_searched
from deduplicated
