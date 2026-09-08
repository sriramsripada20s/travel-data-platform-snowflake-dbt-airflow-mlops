-- ============================================================================
-- MODEL: dim_supplier
-- PURPOSE: One row per supplier -- descriptive attributes only.
-- ============================================================================

with suppliers as (
    select * from {{ ref('stg_suppliers') }}
)

select
    supplier_id,
    supplier_name,
    country,
    supplier_type,
    contract_start_date,
    commission_rate,
    supplier_status,
    datediff('day', contract_start_date, current_date()) as contract_tenure_days
from suppliers