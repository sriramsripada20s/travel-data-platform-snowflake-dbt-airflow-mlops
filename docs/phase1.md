# Phase 1 — Synthetic Data Generation

## 📌 Executive Summary
The goal of Phase 1 is to build a realistic, relationally consistent synthetic data generator for a travel-experience marketplace. 

Rather than generating flat random noise, this module implements explicit behavioral formulas for booking demand and cancellation probabilities. It also creates a secondary "dirty" data copy with intentional quality defects (duplicate records, nulls, negative amounts, out-of-order events), giving downstream dbt models, data quality gates, and Airflow retries real problems to solve.

---

## 🏗️ Execution Blueprint & Pipeline Order

┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. REPO & CONFIG SETUP                                                      │
│    Directory scaffolding, scale controls, and environment configuration     │
└──────────────────────────────────────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. CONTRACTS & BUSINESS RULES                                               │
│    Data schemas (data_contracts.md) & ML signal formulas (business_rules.md) │
└──────────────────────────────────────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. REFERENCE DATA GENERATION                                                │
│    generate_suppliers.py ──► generate_experiences.py ──► generate_customers.py │
└──────────────────────────────────────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. AVAILABILITY ENGINE                                                      │
│    generate_availability.py (Daily time-slots & dynamic base pricing)       │
└──────────────────────────────────────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. BOOKING ENGINE & ML SIGNAL INJECTION                                     │
│    generate_bookings.py (Pass 1: Slot Demand | Pass 2: Risk-Based Cancellation) │
└──────────────────────────────────────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. WEB EVENT FUNNEL GENERATOR                                               │
│    generate_web_events.py (Full-funnel session stream & event budget capping)│
└──────────────────────────────────────┬──────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. DATA QUALITY DEFECT INJECTION                                            │
│    inject_data_quality.py ──► Outputs raw/ (dirty) dataset                  │
└─────────────────────────────────────────────────────────────────────────────┘


---

## 🚀 Detailed Implementation Steps

### Step 1: Repository Scaffolding & Configuration
* Established directory layout:
  * `src/data_generation/` (generator logic)
  * `data/generated/clean/` (pristine target datasets)
  * `data/generated/raw/` (deliberately dirty datasets)
  * `config/`, `docs/`, `tests/`
* Built `config.py` driven by a central `SCALE_FACTOR` environment variable. Reference entity counts scale directly, while transactional entities (availability, bookings, web events) scale naturally based on derived demand.

### Step 2: Data Contracts & Business Rules Specification
* **`docs/data_contracts.md`:** Defined schemas, primary/foreign key relationships, column data types, and strict validation rules.
* **`docs/business_rules.md`:** Documented ground-truth formulas for booking demand (seasonality, popularity, weekend boosts, price elasticity) and cancellation risk (lead time, discount size, booking channel, category risk, prior cancellations) *before* writing code.

### Step 3: Reference Data Generation
* **`generate_suppliers.py`:** Generates supplier metadata (type, contract status, commission rate, country).
* **`generate_experiences.py`:** Builds catalog items linked to valid suppliers, enforcing realistic category/city distributions and pricing bounds.
* **`generate_customers.py`:** Generates customer profiles where `customer_segment` is logically derived from signup tenure (preventing new accounts from being incorrectly classified as dormant).

### Step 4: Inventory & Availability Engine
* **`generate_availability.py`:** Creates slot-level inventory (`1 row = experience_id + date + time_slot`). Slot counts and pricing vary dynamically by season, day of week, and experience category.

### Step 5: Booking Engine & ML Signal Implementation
* **`generate_bookings.py`:** Executes a stateful, two-pass generation algorithm:
  * **Pass 1 (Slot Demand):** Calculates expected bookings using popularity scores, seasonality, weekend factors, price elasticity, and ratings. Samples daily slot demand via Poisson distribution.
  * **Pass 2 (Cancellation Probability):** Processes customer bookings chronologically, compounding cancellation multipliers based on lead time, discount size, booking channel, category, and prior cancellation history.
* **Validation:** Verified that cancellation rates increase monotonically as lead time increases (`<3d` $\rightarrow$ `3-14d` $\rightarrow$ `14-60d` $\rightarrow$ `>60d`), perfectly matching business specifications.

### Step 6: Full-Funnel Web Event Engine
* **`generate_web_events.py`:** Generates behavioral sessions (`SEARCH` $\rightarrow$ `VIEW` $\rightarrow$ `CHECK_AVAILABILITY` $\rightarrow$ `ADD_TO_CART` $\rightarrow$ `CHECKOUT` $\rightarrow$ `PURCHASE`).
* Enforces strict integrity: Every converted session reaching `PURCHASE` matches a real row in `bookings` with an exact 1:1 timestamp linkage.
* Implemented a `MAX_TOTAL_EVENTS` event-budget manager so that high `SCALE_FACTOR` runs maintain realistic non-converting browsing sessions rather than forcing a 100% conversion rate.

### Step 7: Controlled Data Quality Injection
* **`inject_data_quality.py`:** Processes pristine datasets and writes a secondary "dirty" copy into `data/generated/raw/`.
* Injected defects include:
  * Duplicate booking IDs and event IDs
  * Missing `customer_id` values
  * Negative booking amounts
  * Invalid foreign key references
  * Late-arriving booking records
  * Out-of-order event timestamps

### Step 8: Pipeline Orchestration
* **`generate_all.py`:** End-to-end execution script running steps 1–7 with unified timing logs and data assertion integrity checks.

---

## 📊 Final Dataset Summary (`SCALE_FACTOR = 0.3`, `SEED = 42`)

| Dataset Name | Clean Rows | Raw (Dirty) Rows | Injected Quality Defects / Notes |
| :--- | ---: | ---: | :--- |
| **`suppliers`** | **30** | **30** | None (Passed through clean) |
| **`experiences`** | **120** | **120** | None (Passed through clean) |
| **`customers`** | **12,000** | **12,000** | None (Passed through clean) |
| **`availability`** | **101,835** | **101,835** | None (Passed through clean) |
| **`bookings`** | **100,947** | **101,149** | +202 duplicate rows, negative amounts, null FKs |
| **`web_events`** | **1,498,436** | **1,501,433** | +2,997 duplicate events, out-of-order timestamps |

### Key Business Signal Metrics Verified
* **Booking Distribution:** `85.8% CONFIRMED`, `9.5% CANCELLED`, `4.7% REFUNDED` (Overall cancellation/refund rate: `14.2%`).
* **Conversion Linkage:** `PURCHASE` web events match total clean `bookings` exactly (**100,947:100,947**).

---

## ⚠️ Technical Issues Encountered & Resolved

### 1. Missing Availability Output File
* **Root Cause:** File copy-paste error left `generate_availability.py` as an empty file, causing `generate_bookings.py` to throw `FileNotFoundError`.
* **Fix:** Restored full script implementation and added pre-execution file size validation in `generate_all.py`.

### 2. High Initial Demand & Cancellation Rates
* **Root Cause:** `DEMAND_SCALE_CONSTANT` and `BASE_CANCELLATION_RATE` parameters were set too high in early dev runs, producing over 300,000 bookings and an unrealistic 28.7% cancellation rate.
* **Fix:** Retuned `DEMAND_SCALE_CONSTANT` to `1.0` and `BASE_CANCELLATION_RATE` to `0.10`, bringing outputs to 841 bookings/experience and a realistic 14.2% overall cancellation rate.

### 3. Conversion Funnel Saturation at High Scale
* **Root Cause:** A fixed session count cap caused converting purchase sessions to consume the entire session budget at higher scale factors, forcing non-converting browsing sessions to 0 (100% conversion rate).
* **Fix:** Replaced fixed session caps with a dynamic `MAX_TOTAL_EVENTS` budget allocator. Converting sessions are allocated first, and non-converting browsing sessions fill the remaining event budget proportionally.

---

## 📋 Open Technical Items

1. **Formal Unit Testing (`pytest`):**
   - Implement explicit assertion suites for `availability`, `bookings`, `web_events`, and data quality modules under `tests/` (currently validated via inline execution logs).
2. **Schema Contract Documentation Sync:**
   - Update `docs/data_contracts.md` to reflect added `lead_time_days` and `discount_pct`