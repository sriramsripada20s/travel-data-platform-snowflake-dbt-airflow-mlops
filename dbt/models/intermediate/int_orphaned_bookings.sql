-- ============================================================================
-- MODEL: int_orphaned_bookings
-- PURPOSE: Data Quality Exception Queue for invalid or orphaned bookings.
-- ============================================================================
-- Captures the 51 deliberately injected invalid experience_id FK records
-- flagged by dbt data quality tests, ensuring 100% auditability across layers.
-- ============================================================================

with bookings as (
    select * from {{ ref('stg_bookings') }}
),

experiences as (
    select * from {{ ref('stg_experiences') }}
)

select
    b.booking_id,
    b.customer_id,
    b.experience_id,
    b.booking_timestamp,
    b.booking_amount,
    b.booking_status,
    'INVALID_EXPERIENCE_FK' as orphan_reason,
    current_timestamp() as flagged_at
from bookings as b
left join experiences as e
    on b.experience_id = e.experience_id
where e.experience_id is null
