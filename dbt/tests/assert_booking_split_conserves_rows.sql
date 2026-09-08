-- Singular test: int_booking_details + int_orphaned_bookings should together
-- account for every row in stg_bookings, with zero overlap and zero loss.
-- A dbt singular test PASSES when this query returns 0 rows.

with staging_total as (
    select count(*) as row_count from {{ ref('stg_bookings') }}
),

split_total as (
    select
        (select count(*) from {{ ref('int_booking_details') }})
        + (select count(*) from {{ ref('int_orphaned_bookings') }})
        as row_count
)
-- the CROSS JOIN is used because we are joining two subqueries that each return exactly one row 
-- (a single total count), and they share no common key to join on.
select
    staging_total.row_count as staging_row_count,
    split_total.row_count as split_row_count
from staging_total
cross join split_total
where staging_total.row_count != split_total.row_count