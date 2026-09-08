-- ============================================================================
-- MODEL: fact_web_events
-- PURPOSE: One row per behavioral event. experience_id is nullable (SEARCH
-- events have none yet) -- expected, not a defect.
-- ============================================================================

with web_events as (
    select * from {{ ref('stg_web_events') }}
)

select
    event_id,
    customer_id,
    session_id,
    experience_id,
    cast(event_timestamp as date) as date_day,

    event_timestamp,
    event_type,
    device_type,
    traffic_source,
    city_searched

from web_events