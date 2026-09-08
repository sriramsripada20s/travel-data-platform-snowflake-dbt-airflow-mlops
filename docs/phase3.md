# ============================================================================
# PHASE 3 SUMMARY: DATA TRANSFORMATIONS & QUALITY CONTROL (dbt)
# ============================================================================
# GOAL:
# Take the "dirty" raw data from Phase 2 and transform it into a clean, tested,
# and dashboard-ready Star Schema.
#
# KEY PHILOSOPHY:
# We do NOT secretly hide or fix bad data. We handle bad data intentionally:
# 1. Structural Fixes (Staging): Remove exact row duplicates.
# 2. Monitoring Signals (Staging Tests): Log soft warnings for bad raw data.
# 3. Quality Gates (Intermediate Tests): Enforce hard stops if our code breaks.
# ============================================================================

-- ============================================================================
-- TOOLING NOTES & LESSONS (dbt-Fusion Engine)
-- ============================================================================
-- We used `dbt-fusion` (a fast, Rust-based engine) instead of classic `dbt-core`.
-- Fusion is stricter than older engines:
-- 1. All test parameters MUST be grouped inside an `arguments:` block in YAML.
-- 2. `dbt deps` MUST run first so package functions like `dbt_utils` work.
-- ============================================================================


-- ============================================================================
-- LAYER 1: STAGING LAYER (6 Models)
-- ============================================================================
-- MODELS: stg_suppliers, stg_experiences, stg_customers, stg_availability,
--         stg_bookings, stg_web_events
--
-- WHAT THIS LAYER DOES:
-- - Standardizes column names and data types.
-- - Removes structural duplicate rows in bookings (202) and web events (2,997).
--
-- WHAT THIS LAYER DOES NOT DO:
-- - It DOES NOT fix missing customer IDs, negative amounts, or bad foreign keys.
--   We leave those errors alone so our dbt tests can catch and report them!
--
-- TEST RESULTS (22 Tests):
-- - 19 Passed cleanly.
-- - 3 Issued Warnings (101 missing customer IDs, 51 negative prices, 51 bad FKs).
-- ============================================================================


-- ============================================================================
-- LAYER 2: INTERMEDIATE LAYER (4 Models)
-- ============================================================================
-- MODELS: 
-- 1. int_booking_details       --> Enriched bookings (clean inner joins only).
-- 2. int_orphaned_bookings     --> Quarantine table holding the 51 bad FK rows.
-- 3. int_customer_activity     --> One row per customer (LTV & website behavior).
-- 4. int_experience_daily_metrics --> One row per tour + date (demand & capacity).
--
-- CUSTOM SINGULAR TEST: assert_booking_split_conserves_rows.sql
-- Mathematically proves that: 
--     stg_bookings = int_booking_details + int_orphaned_bookings
-- Zero rows or revenue are silently lost!
--
-- ARCHITECTURAL DECISION (Where does the Quality Gate belong?):
-- - Hard Stop Gates (`severity: error`) belong on cleaned intermediate models,
--   NOT on dirty raw landing models.
-- - Why? If raw data fails a hard gate, `dbt build` halts and cancels 
--   `int_orphaned_bookings`—the exact table built to report the bad rows!
-- - Moving the hard gate to `int_booking_details` ensures that raw data issues 
--   warn us, while pipeline transformation bugs stop execution.
-- ============================================================================


-- ============================================================================
-- LAYER 3: MARTS LAYER (7 Models)
-- ============================================================================
-- DIMENSIONS: dim_customer, dim_supplier, dim_experience, dim_date
-- FACTS:      fact_bookings, fact_web_events, fact_experience_availability
--
-- WHAT THIS LAYER DOES:
-- - Builds a standard Kimball Star Schema for business dashboards and ML models.
-- - Fact tables hold numbers and keys; Dimension tables hold descriptions.
-- - Uses `dim_date` (built via `dbt_utils.date_spine`) as a shared calendar 
--   to easily connect web traffic, bookings, and inventory across time.
--
-- DESIGN DECISION (No separate 'analytics' layer):
-- We skipped creating a 4th "analytics" layer because our Marts and Intermediate 
-- rollups are already 100% dashboard-ready.
-- ============================================================================


-- ============================================================================
-- BUGS & BATTLE-TESTED LESSONS LEARNED
-- ============================================================================
-- 1. Empty Pasted Files: If dbt says "nothing to do", check if your SQL/YAML 
--    file was accidentally pasted as an empty file!
-- 2. Jinja Comments: Use `{# comment #}` inside Jinja macros, NOT `--`. 
--    Using `--` accidentally pastes text into your Snowflake schema names.
-- 3. Windows Folder Renaming: Windows ignores case-only folder renames 
--    (e.g., `Marts` -> `marts`). Rename to a temp folder first (`Marts` -> `temp` -> `marts`).
-- 4. Calendar Spines: `dbt_utils.date_spine` excludes its end date. Always add 
--    a buffer day to avoid cutting off late-night timestamps!
-- ============================================================================


-- ============================================================================
-- FINAL VERIFIED PROJECT STATE
-- ============================================================================
-- TOTAL MODELS: 17 (6 Staging + 4 Intermediate + 7 Marts)
-- TOTAL TESTS:  57 (54 Passed, 3 Soft Warnings, 0 Failures)
--
-- SUMMARY OF WARNINGS (All 3 are expected & documented):
-- 1. stg_bookings.customer_id is null (~101 rows)
-- 2. stg_bookings.booking_amount < 0 (~51 rows)
-- 3. stg_bookings.experience_id bad foreign key (~51 rows)
--
-- VERIFICATION CHAIN COMPLETE:
-- Business rules described it -> Python generator injected it -> Snowflake loaded it 
-- -> dbt tested and isolated it. All 4 checkpoints match perfectly!
-- ============================================================================