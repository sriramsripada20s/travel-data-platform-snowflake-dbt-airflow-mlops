# ============================================================================
# PHASE 4 SUMMARY: BUSINESS ANALYTICS & EXECUTIVE DASHBOARD (Streamlit + Snowflake)
# ============================================================================
# GOAL:
# Build an interactive executive dashboard using Streamlit that queries 
# Snowflake's Marts and Intermediate tables in real time to visualize key 
# business KPIs, revenue trends, and user conversion funnels.
# ============================================================================

-- ============================================================================
-- DASHBOARD LAYOUT & METRIC SCOPING DESIGN
-- ============================================================================
-- 1. Filter Control Row:
--    - Global dropdowns for City and Category + a manual data refresh button.
--
-- 2. Executive KPI Cards (Top Row):
--    - Total Bookings, GMV ($), Cancellation Rate (%) --> Scoped to City/Category filters.
--    - Repeat Customer Rate (%) --> GLOBAL ONLY. Scoped to total customer history 
--      (INT_CUSTOMER_ACTIVITY) because repeat status reflects a user's entire 
--      lifetime behavior, not just filtered sub-transactions.
--
-- 3. Monthly Revenue & Booking Trends:
--    - Monthly bar chart joining FACT_BOOKINGS -> DIM_DATE -> DIM_EXPERIENCE.
--
-- 4. Geographic Revenue Breakdown:
--    - Horizontal bar chart ranking Top Cities by confirmed revenue.
--
-- 5. User Conversion Funnel (SEARCH -> PURCHASE):
--    - Distinct session counts from FACT_WEB_EVENTS.
--    - SCOPING NOTE: Unfiltered by City/Category! Top-of-funnel events (SEARCH) 
--      have a NULL experience_id and would be accidentally dropped by catalog filters.
--
-- 6. Top Experiences Table:
--    - Ranks top 10 experiences by booking volume, average capacity utilization, 
--      and confirmed revenue using INT_EXPERIENCE_DAILY_METRICS.
-- ============================================================================


-- ============================================================================
-- TECHNICAL BUGS FIXED DURING DEVELOPMENT
-- ============================================================================
-- 1. Streamlit Sibling Import Errors:
--    - Issue: `from streamlit_app.connection import ...` failed because there was 
--      no installed `streamlit_app` package wrapper.
--    - Fix: Changed to bare module imports (`from connection import ...`) since 
--      Streamlit automatically adds the script's root directory to sys.path.
--
-- 2. Snowflake Decimal vs. Float TypeError:
--    - Issue: Snowflake returns NUMBER/DECIMAL columns as `decimal.Decimal` objects, 
--      causing `TypeError` when performing float math (e.g., `utilization * 100`).
--    - Fix: Added central casting inside `run_query()` in `queries.py` to automatically 
--      convert all `Decimal` values to `float` across all DataFrame outputs.
--
-- 3. Streamlit Deprecation Warnings (`use_container_width`):
--    - Streamlit is migrating to `width='stretch'` / `width='content'`.
--    - Left as a non-blocking warning for now (deprecation scheduled post-2025).
-- ============================================================================


-- ============================================================================
-- DATA INVESTIGATION FINDING: Museum Capacity Utilization
-- ============================================================================
-- FINDING:
-- High-capacity experience categories (like Museum tours in Dubai) showed low 
-- daily utilization rates (e.g., 0.3% - 6.0%).
--
-- ROOT CAUSE ANALYSIS:
-- - Verified daily metrics calculation logic: daily bookings (6-24/day) were 
--   accurately calculated with zero missing days.
-- - In Phase 1, `generate_experiences.py` set default daily museum capacity 
--   very high (~393+ slots/day), while `generate_bookings.py` generated modest 
--   daily booking numbers.
-- - The numbers are mathematically correct—the generator parameters were simply 
--   not calibrated for high-capacity venue utilization.
--
-- DECISION:
-- Left as-is. Re-calibrating Phase 1 generator constants would require re-running 
-- the full data pipeline (generation -> S3 landing -> Snowflake COPY -> dbt build) 
-- for a purely cosmetic metric tweak.
-- ============================================================================


-- ============================================================================
-- FINAL VERIFIED DASHBOARD STATE
-- ============================================================================
-- - Streamlit application (`app.py`) runs cleanly on `localhost:8501`.
-- - Securely queries Snowflake `MARTS` and `INTERMEDIATE` schemas using 
--   `snowflake-connector-python` with connection caching (`@st.cache_data`).
-- - All six dashboard sections render live data with functional global filters.
-- ============================================================================