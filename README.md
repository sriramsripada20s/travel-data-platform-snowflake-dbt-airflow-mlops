# Travel Experience Data & ML Intelligence Platform Using Snowflake, dbt, Airflow, Machine Learning, CI/CD

An end-to-end **data engineering, analytics engineering, machine learning, and MLOps platform** for a travel-experience marketplace — built on **Snowflake, dbt, Apache Airflow 3.x, and Python**, with a fully automated CI/CD pipeline and a live analytics dashboard.

The platform ingests marketplace activity daily, transforms it through a tested dimensional model, forecasts booking demand, and orchestrates the entire lifecycle end to end — from raw data landing in S3 to a champion/challenger ML model making real promotion decisions, with every stage validated by automated tests and deployed through GitHub Actions.

[![dbt Core](https://img.shields.io/badge/dbt--core-1.12-FF694A?style=flat&logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![Snowflake](https://img.shields.io/badge/Snowflake-Data%20Cloud-29B5E8?style=flat&logo=snowflake&logoColor=white)](https://www.snowflake.com/)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-3.x-017CEE?style=flat&logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)
[![AWS S3](https://img.shields.io/badge/AWS-S3-569A31?style=flat&logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=flat&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-2B5B84?style=flat&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io/)
[![Streamlit](https://img.shields.io/badge/Streamlit--in--Snowflake-Dashboard-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?style=flat&logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Slack](https://img.shields.io/badge/Slack-Alerting-4A154B?style=flat&logo=slack&logoColor=white)](https://slack.com/)
---

## Business Problem

Travel marketplaces process bookings, availability, and behavioral data across multiple sources — booking transactions, real-time inventory feeds, and customer browsing/conversion events — all of which must stay reliable as the platform scales.

* **Fragmented Data & Quality Risk:** Duplicate bookings, missing customer IDs, and invalid foreign keys routinely enter raw data undetected, silently corrupting downstream revenue and capacity reporting if not caught before they reach business-facing tables.
* **Reactive Demand Planning:** Booking cancellations and capacity shortfalls are typically discovered only after they've already affected revenue, rather than forecasted with enough lead time to act on.
* **Manual, Engineer-Dependent Reporting:** Business stakeholders depend on data engineers to write ad-hoc SQL for daily questions — today's bookings, revenue by city, which experiences are near capacity — with no self-service path to the same answers.

💡 **Proposed Solution:** An automated data and ML platform built on AWS S3, Snowflake, dbt, and Apache Airflow that isolates data-quality defects at the staging layer via hard-gated tests, models a governed dimensional layer feeding a champion/challenger demand-forecasting pipeline, and surfaces self-service analytics through a live Streamlit-in-Snowflake dashboard — with every change to the pipeline validated by automated CI/CD before it reaches production.

## 📌 Architecture Overview

Data flows from a daily incremental generator through AWS S3 staging into Snowflake, where it undergoes automated validation, dbt dimensional transformations, a champion/challenger demand-forecasting pipeline, and a live Streamlit-in-Snowflake dashboard — all orchestrated end to end by Apache Airflow and deployed through automated CI/CD.

<img width="1121" height="681" alt="image" src="https://github.com/user-attachments/assets/012e6565-a03d-44fa-beb7-bc9dc75418be" />

* **Data Sources:** Batch historical generator (one-time full-year backfill) and a daily incremental generator producing bookings, availability, and web-event activity — statistically consistent with each other via shared demand/cancellation logic.
* **Ingestion:** Python generators writing partitioned CSVs to AWS S3, loaded into Snowflake via `COPY INTO` — historical bulk load and daily append-only incremental path, both orchestrated by Airflow.
* **Storage (Landing):** AWS S3 (partitioned by date) and Snowflake `RAW` schema landing tables.
* **Processing / Transformation:** dbt Core (Staging → Intermediate → Marts, including a dedicated `marts/ml` feature layer) on Snowflake, with a hard-fail data-quality gate on booking foreign-key integrity.
* **Data Warehouse:** Snowflake (`TRAVEL_PLATFORM`).
* **Orchestration:** Apache Airflow 3.x, two DAGs (daily ingestion + weekly ML training), deployed via Docker Compose.
* **Machine Learning:** scikit-learn / XGBoost demand forecasting, 3-algorithm comparison, with a champion/challenger promotion gate evaluated weekly.
* **Analytics:** Streamlit-in-Snowflake live dashboard (6 charts), plus a dbt Semantic Layer defining governed metrics (`total_bookings`, `gmv`, `cancellation_rate`, `repeat_customer_rate`), queryable via `dbt sl query`.
* **CI/CD:** GitHub Actions — 6 automated checks with enforced branch protection, plus auto-deploy of dbt docs (GitHub Pages) and the Streamlit dashboard on every merge to `main`.

## Project Phase Plan

| Phase | Notes |
|---|---|
| 0 — Business design, architecture, KPIs | Business Problem, Understanding, Architecture and Tech Stack Used |
| 1 — Synthetic data generation | One-time historical batch (Sep 2025–Sep 2026) + a separate daily incremental generator, both independently verified |
| 2 — Snowflake + SQL | S3 ↔ Snowflake via `COPY INTO`, both the historical bulk load and the daily append-only incremental path |
| 3 — dbt + dimensional modeling | 21 models, 67 tests — **no separate `analytics/` layer** (see note below) |
| 4 — Business analytics + KPIs | Delivered as a live dashboard (Streamlit-in-Snowflake), not additional dbt models |
| 5 — ML feature engineering | Leakage-safe rolling-window features, split into 4 focused dbt models |
| 6 — Baseline + demand forecasting model | 3-algorithm comparison (XGBoost, Random Forest, Ridge) — see Machine Learning section for the honest result |
| 7 — Airflow 3.x orchestration | Two DAGs, deployed via Docker Compose, verified end to end including a real champion/challenger decision |
| 8 — CI/CD | CI: 6 automated checks + enforced branch protection, proven end-to-end. CD: dbt docs auto-published to GitHub Pages, Streamlit dashboard auto-deployed to Snowflake, both on every merge to `main` |
| 9 — Slack alerting | Built into both DAGs (failure callback + end-of-run summary) as part of Phase 7 |

**Airflow DAG Pipeline: showing a successful `travel_platform_daily_pipeline` run (all green).**

<img width="1830" height="876" alt="image" src="https://github.com/user-attachments/assets/1c59e50a-c7b4-45a9-9834-e8d38fd5dc87" />

---

🎥 *Watch Project Video Below for demonstration*
*https://github.com/sriramsripada20s/travel-data-platform-snowflake-dbt-airflow-mlops/issues/1*

## Project Goal

Build a production-style data and ML platform for a travel marketplace where customers discover and book experiences such as:

* Attractions
* Guided tours
* Museums
* Theme parks
* Cruises
* Food tours
* Adventure activities
* City experiences

The platform ingests marketplace data daily, transforms it through a tested dimensional model, generates business KPIs on a live dashboard, forecasts experience demand with a champion/challenger ML pipeline, and orchestrates the complete lifecycle — from data generation through model promotion — using Apache Airflow, deployed and validated through automated CI/CD. End to end, not as disconnected demos.

## Business Problem

A travel marketplace generates data across the customer journey:

```text
Customer
   |
   v
Search Destination
   |
   v
View Experience
   |
   v
Check Availability
   |
   v
Add to Cart
   |
   v
Checkout
   |
   v
Booking
   |
   v
Experience
```

As the marketplace grows, teams need reliable answers to questions such as:

* How many bookings are happening?
* Which destinations are growing?
* Which experiences generate the most revenue?
* What is the booking conversion rate?
* What is the cancellation rate?
* Which customers make repeat bookings?
* Which experiences are approaching capacity?
* How much demand should we expect tomorrow?
* Which bookings have a high probability of cancellation?

This project builds the data platform needed to answer those questions — and a live dashboard so the answers are actually consumable, not just queryable.

---

📸 *The Streamlit dashboard (all 6 charts) — the strongest single visual proof-point in this project.*
<img width="1876" height="900" alt="image" src="https://github.com/user-attachments/assets/4b44a64b-007b-40fa-96ff-05cee01d5605" />
<img width="1905" height="906" alt="image" src="https://github.com/user-attachments/assets/56b307b5-fd52-468b-9d56-0b13aeb8672d" />

## Business KPIs

Delivered as a live Streamlit-in-Snowflake dashboard, not a static report:

* Total bookings, GMV, cancellation rate, repeat customer rate (KPI cards)
* Bookings over time (trend)
* Top cities by revenue
* Booking funnel (search → purchase)
* Top experiences (bookings, utilization, revenue)
* Cancellation rate by lead-time bucket — directly visualizes the demand-signal design from `docs/business_rules.md`
* Booking channel mix

The analytics layer was built and validated before ML was introduced, so the underlying business data was trusted first.

---
## Technology Stack

| Technology | Purpose |
|---|---|
| **Python** | Synthetic data generation (batch + daily incremental), validation, ML, utility logic |
| **SQL** | Analytics, transformations, feature engineering, business logic |
| **Snowflake** | Cloud analytical warehouse, compute, and app hosting (Streamlit-in-Snowflake) |
| **dbt** | Data modeling, transformations, testing, documentation, lineage |
| **Apache Airflow 3.x** | Workflow orchestration — two DAGs, scheduling, dependencies, retries, monitoring |
| **scikit-learn / XGBoost** | Machine learning model development |
| **Docker** | Containerized Airflow deployment (Postgres, webserver, scheduler, DAG processor) |
| **Streamlit** | Live analytics dashboard, hosted natively in Snowflake |
| **Slack** | Pipeline failure alerts and end-of-run summaries |
| **Git / GitHub** | Version control, documentation, portfolio hosting |
| **GitHub Actions** | CI (6 checks, branch protection enforced) and CD (dbt docs → GitHub Pages, Streamlit auto-deploy) — both fully built and proven |

---

## Core Data Domains

Six datasets underpin the platform.

### Customers
**Grain:** one row per customer.
```text
customer_id
signup_date
country
preferred_language
acquisition_channel
customer_segment
```

### Suppliers
**Grain:** one row per supplier.
```text
supplier_id
supplier_name
country
supplier_type
contract_start_date
commission_rate
supplier_status
```

### Experiences
**Grain:** one row per bookable experience.
```text
experience_id
experience_name
city
country
category
supplier_id
base_price
capacity
rating
active_flag
```

### Bookings — the primary transactional dataset
**Grain:** one row per booking.
```text
booking_id
customer_id
experience_id
booking_timestamp
experience_date
number_of_guests
ticket_price
discount_amount
booking_amount
booking_status
payment_status
booking_channel
currency
lead_time_days       (added post-Phase-5, feeds ML features directly)
discount_pct         (added post-Phase-5, feeds ML features directly)
```

### Availability & Pricing
**Grain:** experience + date + time slot.
```text
experience_id
experience_date
time_slot
total_capacity
available_capacity
price
```

### Web / App Events
**Grain:** one row per behavioral event.
```text
SEARCH
VIEW_EXPERIENCE
CHECK_AVAILABILITY
ADD_TO_CART
CHECKOUT
PURCHASE
```
Used to reconstruct the marketplace conversion funnel — visualized live on the dashboard.

---

---

## Dataset Scale

| Dataset | Target (full scale) | Actual (current run, `SCALE_FACTOR=0.3`) |
|---|---:|---:|
| Suppliers | 75–100 | 30 |
| Experiences | 300–500 | 120 |
| Customers | 30K–50K | 12,000 |
| Bookings | 200K–300K | ~101,000 (batch) + daily incremental growth |
| Availability | 250K–500K | ~102,000 |
| Web Events | 750K–1.5M | ~1.5M |

---

## Data Relationships

```text
CUSTOMER
    |
    +------------------------------+
    |                              |
    v                              v
BOOKINGS                       WEB EVENTS
    |                              |
    v                              |
EXPERIENCE <-----------------------+
    |
    v
SUPPLIER


EXPERIENCE
    |
    v
AVAILABILITY
```

```text
bookings.customer_id       -> customers.customer_id
bookings.experience_id     -> experiences.experience_id
experiences.supplier_id    -> suppliers.supplier_id
availability.experience_id -> experiences.experience_id
web_events.customer_id     -> customers.customer_id
web_events.experience_id   -> experiences.experience_id
```

---

## Synthetic Data — two generators, two purposes

Real marketplace data is proprietary, so the project generates realistic synthetic data — with two distinct generators serving different purposes, not one:

- **Batch generator** (`src/data_generation/`) — one-time historical backfill covering a full year, run once, producing the ~1.2M-row dataset described below.
- **Incremental generator** (`src/data_generation/incremental/`) — generates exactly one new simulated day at a time, called daily by Airflow, using the *same* demand/cancellation logic (shared via `business_logic.py`) so incremental data stays statistically consistent with the historical backfill.

Both preserve real business relationships rather than generating independent random rows — e.g. a customer's booking is backed by a matching web-events session:

```text
Customer C100
     |
     v
SEARCH Rome -> VIEW Colosseum -> CHECK_AVAILABILITY -> ADD_TO_CART -> CHECKOUT -> PURCHASE
     |
     v
Booking B98231
```
## Data Warehouse Model

### Booking Model
```text
                         DIM_DATE
                             |
DIM_CUSTOMER -------- FACT_BOOKINGS -------- DIM_EXPERIENCE
                                             |
                                       DIM_SUPPLIER
```

### Behavioral Model
```text
DIM_CUSTOMER
      |
FACT_WEB_EVENTS -------- DIM_EXPERIENCE
      |
   DIM_DATE
```

### Availability Model
```text
DIM_EXPERIENCE
       |
FACT_EXPERIENCE_AVAILABILITY
       |
    DIM_DATE
```

All marts are `materialized='table'` (full refresh), a deliberate choice over incremental materialization — at this data volume a full rebuild costs seconds, and it avoids a real bug class (a cancellation on an already-loaded past booking silently not propagating through an incremental filter).

---

## dbt Architecture — as actually built

```text
RAW -> STAGING -> INTERMEDIATE -> MARTS
```

```text
dbt/models/
├── staging/                       (6 models)
│   ├── stg_customers.sql
│   ├── stg_suppliers.sql
│   ├── stg_experiences.sql
│   ├── stg_bookings.sql             (dedup via QUALIFY)
│   ├── stg_availability.sql
│   └── stg_web_events.sql           (dedup via QUALIFY)
│
├── intermediate/                  (4 models)
│   ├── int_booking_details.sql      (inner-joined, orphan-FK excluded, hard test gate here)
│   ├── int_orphaned_bookings.sql    (the excluded rows, kept visible — not in the original plan)
│   ├── int_customer_activity.sql
│   └── int_experience_daily_metrics.sql
│
└── marts/                         (7 models + 4 ML feature models)
    ├── dim_customer.sql, dim_supplier.sql, dim_experience.sql, dim_date.sql
    ├── fact_bookings.sql, fact_web_events.sql, fact_experience_availability.sql
    └── ml/
        ├── ml_daily_price.sql
        ├── ml_base_features.sql
        ├── ml_rolling_features.sql    (leakage-safe: every window excludes the current row)
        └── ml_demand_features.sql     (final, training-ready table)
```

**No `analytics/` layer was built.** The original plan called for a fourth tier (`mart_booking_funnel.sql`, etc.) on top of marts — dropped after review: everything it would compute is already directly queryable from the marts, current dbt convention treats business-area marts as the final layer, and with one project and no competing BI consumers the abstraction wasn't earning its cost. See `docs/phase_3_summary.md`.

**`ml_cancellation_features.sql` was never built** — the secondary ML use case was deprioritized.

67 tests total: 64 pass, 3 deliberate `WARN`s (documenting known injected defects), 0 unexpected failures.

---

## Machine Learning

### Primary Use Case — Demand Forecasting

> How many bookings will each experience receive on a future date?

**Grain:** experience + date.

**Model development progression, as actually run:**
```text
Naive baseline (yesterday's value)
      |
Rolling 7-day average
      |
Rolling 28-day average   <- strongest baseline, MAE 1.188
      |
Feature engineering (leakage-safe, dbt-built)
      |
Three algorithms trained and compared:
  - XGBoost         MAE 1.182
  - Random Forest   MAE 1.189
  - Ridge (linear)  MAE 1.181  <- current champion
```

**Honest finding, not just a leaderboard:** all three algorithms landed within 0.008 MAE of each other — statistically indistinguishable. Ridge, a purely linear model with no ability to learn interaction effects, tied with tree-based models that can. This indicates the relationship between the engineered features and booking demand is close to linear, dominated by an experience's own recent booking momentum (`bookings_prev_28d_avg` accounted for ~54% of feature importance in the XGBoost run) — the additional features (price, category, calendar context) add only marginal refinement. See `docs/phase_6_summary.md` for the full interpretation.

---

## Airflow Orchestration — two DAGs, not one

Built as two separate DAGs, deliberately split by schedule rather than one monolith:

**`travel_platform_daily_pipeline`** (`@daily`, `catchup=True`):
```text
generate_data -> validate_data -> [upload x3 -> wait x3 -> load x3]
   -> update_pipeline_state -> dbt_build -> build_ml_features -> send_summary
```

**`ml_training_pipeline`** (weekly, Mondays, `catchup=False`):
```text
train_model -> evaluate_model -> decide_promotion
   -> {promote_champion | keep_current_champion} -> generate_predictions -> send_summary
```

**Why split:** with ~200 new bookings/day, daily retraining would give each run a negligible new increment to learn from — not worth the compute. Weekly gives a meaningfully larger accumulation between retrains.

**Deployed via Docker Compose** — 5 containers (Postgres, webserver/API-server, scheduler, DAG processor, plus the init job). Getting this running surfaced several genuine, undocumented-at-the-time Airflow 3 breaking changes (renamed commands, a new default auth manager, a now-mandatory standalone DAG processor) — full root-cause detail in `docs/phase_7_troubleshooting_log.md`.

📸 *Airflow Connections page (`snowflake_default`, `aws_default`, `slack_default`)*
<img width="1045" height="464" alt="image" src="https://github.com/user-attachments/assets/e43118b4-0aef-4791-9b2d-3e0338ac872b" />

📸 *The Slack message reading "Weekly retrain complete. Candidate ridge (MAE 1.185) vs. champion (MAE 1.181). Promoted: False" — this is the single best proof-point that the MLOps gate makes real, correct decisions, not just runs successfully.*
<img width="1399" height="743" alt="image" src="https://github.com/user-attachments/assets/18b361a6-0a0c-4a0c-9cb6-253937073aad" />

---

## CI/CD Pipeline

### CI — six checks, enforced via branch protection

Every pull request runs six automated checks, verified end-to-end with a real test PR showing the merge button disabled until all six passed:

| Check | What it validates |
|---|---|
| `lint` | Python (`ruff`) + SQL (`sqlfluff`) — real bug patterns, not just style |
| `secrets-scan` | No credentials ever committed (`gitleaks`) |
| `dbt-parse` | Every dbt model compiles (dummy credentials, no live warehouse needed) |
| `docker-build-and-dag-tests` | 10 DAG integrity tests, run **inside the real deployment image** — not just against a bare local Airflow install |
| `unit-tests` | 25 tests covering the demand/cancellation formulas (`business_logic.py`) and the leakage-safe train/test split (`ml/data_loader.py`) |
| `dbt-slim-ci` | `dbt build --select state:modified+ --defer` — only rebuilds/tests what actually changed in the PR, deferring everything unchanged to production's existing state, compared against a `manifest.json` published on every merge to `main` |

### CD — dbt docs and the dashboard, both auto-deployed on merge

Two independent, path-scoped workflows, authenticating via a dedicated `production` GitHub Environment (secrets scoped there, not at the repo level):

| Workflow | Triggers on | Does |
|---|---|---|
| `deploy-docs.yml` | Changes to `dbt/` merged to `main` | `dbt docs generate` against real Snowflake, publishes the full lineage/catalog site to GitHub Pages |
| `deploy-streamlit.yml` | Changes to `streamlit_app/` merged to `main` | `snow streamlit deploy --replace` — updates the existing `TRAVEL_PLATFORM.MARTS.TRAVEL_DASHBOARD` app in place (same URL every time, never a new object) |

📊 **[Live dbt documentation & lineage](https://sriramsripada20s.github.io/travel-data-platform-snowflake-dbt-airflow-mlops/)** — auto-published on every merge to `main`.

## Repository Structure — as actually built

```text
travel-data-platform-snowflake-dbt-airflow-mlops/

├── airflow/
│   ├── dags/
│   │   ├── travel_platform_daily_pipeline.py
│   │   └── ml_training_pipeline.py
│   ├── dbt_profiles/            (profiles.yml for dbt inside the container)
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   └── requirements.txt
│
├── data/
│   └── generated/
│       ├── clean/ , raw/         (batch output)
│       └── incremental/          (daily output, dt=YYYY-MM-DD partitioned)
│
├── dbt/
│   └── models/
│       ├── staging/ , intermediate/ , marts/ (incl. marts/ml/)
│
├── ml/
│   ├── data_loader.py, evaluate.py, train_models.py
│   └── (registry.json + saved models live in /models, one level up)
│
├── models/
│   ├── registry.json
│   └── *_demand_forecast.joblib, champion_demand_forecast.joblib
│
├── src/
│   └── data_generation/
│       ├── (11 batch generator files)
│       └── incremental/
│           ├── business_logic.py     (shared demand/cancellation formulas)
│           ├── generate_incremental.py
│           └── state.py
│
├── streamlit_app/
│   ├── streamlit_app.py         (Streamlit-in-Snowflake, single source of truth)
│   ├── snowflake.yml            (Snowflake CLI project definition, used by deploy-streamlit.yml)
│   ├── pyproject.toml           (dependency spec for the CLI deploy)
│   └── environment.yml
│
├── sql/
│   ├── raw/ , state/
│
├── tests/
│   ├── unit/                    (25 tests — business_logic.py, ml/data_loader.py)
│   └── airflow/                 (10 DAG integrity tests, run inside the Docker image)
│
├── .github/
│   └── workflows/
│       ├── ci.yml                (6 jobs — see CI/CD Pipeline section)
│       ├── dbt-manifest.yml      (publishes the Slim CI comparison manifest)
│       ├── deploy-docs.yml       (dbt docs -> GitHub Pages, on merge)
│       └── deploy-streamlit.yml  (dashboard -> Snowflake, on merge)
│
├── docs/
│   ├── phase_1_summary.md ... phase_7_summary.md
│   ├── phase_7_troubleshooting_log.md
│   ├── phase_8_ci_summary.md
│   ├── data_contracts.md
│   └── business_rules.md
│
├── .gitignore
└── README.md
```

