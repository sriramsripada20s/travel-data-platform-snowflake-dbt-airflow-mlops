# Phase 7 — Airflow Orchestration & Streamlit Deployment

## Executive Overview
Phase 7 takes the manual Python scripts and Snowflake loads built in Phases 1–6 and converts them into two production-grade, self-monitoring **Airflow 3.x** pipelines. Additionally, the local Streamlit dashboard was redeployed as a persistent, native **Streamlit-in-Snowflake** application.

---

## 1. Pipeline Architecture: Dual-DAG Design

Rather than building a single monolithic pipeline, tasks are deliberately split into two DAGs with distinct schedules:

┌───────────────────────────────────────────────────────────────────────────────────┐
│ DAILY PIPELINE: travel_platform_daily_pipeline (@daily, catchup=True)             │
│                                                                                   │
│  generate_data ──► validate_data ──► [upload ×3 ──► wait ×3 ──► load ×3]          │
│                                                                 │                 │
│  send_summary ◄── dbt_build ◄── build_ml_features ◄── update_pipeline_state ──────┘
└───────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────┐
│ WEEKLY ML PIPELINE: ml_training_pipeline (0 6 * * 1 - Mondays, catchup=False)     │
│                                                                                   │
│  train_model ──► evaluate_model ──► decide_promotion                              │
│                                            ├──► promote_champion ─────┐           │
│                                            └──► keep_champion ────────┴─► predict │
└───────────────────────────────────────────────────────────────────────────────────┘


### Why Split Schedules?
* **Daily Ingestion Pipeline:** Runs daily to generate, stage, load, and transform ~200 new daily bookings.
* **Weekly Retraining Pipeline:** Retraining an ML model daily on ~200 new rows produces negligible model updates while wasting compute. A weekly cadence pools ~1,400 new records, offering a statistically meaningful dataset for retraining.

---

## 2. Airflow Production Feature Mapping

| Airflow Feature | Project Implementation | Value Delivered |
| :--- | :--- | :--- |
| **TaskFlow API** | `@dag`, `@task`, and `@task.branch` decorators throughout. | Clean, pythonic DAG code with implicit XCom data passing. |
| **Logical Dates (`ds`)** | `generate_data` uses Airflow's execution date (`ds`) as the single source of truth. | Makes backfilling deterministic; ignores system clock drift. |
| **Backfill Engine** | `catchup=True` with `start_date = 2026-09-09`. | Automatically executes missing historical days in order. |
| **Secure Connections** | `SnowflakeHook`, `S3Hook`, and `SlackWebhookHook`. | Eliminates hardcoded `.env` secrets or API tokens in DAG files. |
| **Deferrable Sensors** | `S3KeySensor(deferrable=True)`. | Releases worker thread slots while waiting for S3 file availability. |
| **Dynamic Task Mapping** | `.expand()` mapped across availability, bookings, and web_events. | Spawns parallel task instances for S3 staging and Snowflake `COPY INTO`. |
| **Champion/Challenger Gate** | `@task.branch` routes to `promote_champion` or `keep_current_champion`. | Automates MLOps model promotion based on MAE evaluation. |
| **Data-Quality Gates** | Pre-upload `validate_data` + Post-load `dbt build` test suite. | Halts downstream ML execution if primary keys or FK checks fail. |
| **Resilience & Retries** | `retries=3` on network-heavy `load_snowflake_raw` tasks. | Automatically recovers from transient network or database connection blips. |
| **Trigger Rules** | `none_failed_min_one_success` (post-branch) & `all_done` (summary). | Guarantees notification delivery regardless of pipeline outcome. |
| **Real-Time Monitoring** | `on_failure_callback` tied to `_on_dag_failure`. | Sends an instant Slack alert detailing the exact task, DAG, and date that failed. |

---

## 3. Idempotency Guardrail Fix

> **The Problem Identified:**
> Re-running a succeeded date originally caused booking counter functions to re-query Snowflake for the highest `booking_id`. Because previous runs had already committed, the generator would create a second set of bookings with *new* IDs for that same date, silently doubling data volume.
> 
> **The Fix:**
> Added a strict pre-execution check inside `generate_data`:
> If `RAW_BOOKINGS` already contains records for the target execution date (`ds`), the task raises an error and halts execution before generating new CSVs.

---

## 4. Production Verification Results

The daily pipeline was tested and verified under real execution conditions across consecutive dates, producing exact row matches across all layers:

| Target Table | Manual Run (2026-09-08) | Airflow Automated Run (2026-09-09) |
| :--- | :--- | :--- |
| `RAW_AVAILABILITY` | 279 rows | 279 rows |
| `RAW_BOOKINGS` | 205 rows | 205 rows |
| `MARTS.FACT_BOOKINGS` | 205 rows (Exact match) | 205 rows (Exact match) |
| `RAW.PIPELINE_STATE` | `2026-09-08` | `2026-09-09` |

### Weekly ML Gate Verification:
During evaluation, a newly trained Ridge model candidate achieved an **MAE of 1.185**, failing to beat the active Champion model's **MAE of 1.181**. The gate correctly evaluated `Promoted: False` and routed execution to `keep_current_champion`, confirming that the rejection gate works properly under real conditions.

---

## 5. Native Streamlit-in-Snowflake Deployment

The local dashboard was migrated directly inside Snowflake as a native app (`TRAVEL_PLATFORM.MARTS.TRAVEL_DASHBOARD`).

* **Decoupled Architecture:** Airflow ensures the underlying data is fresh (`dbt_build` and `build_ml_features`), while Snowflake hosts the web interface natively.
* **Enhanced Analytics:** Added new visualizations, including **Cancellation Rate by Lead-Time Bucket** and **Booking Channel Mix**, exposing underlying business rules directly to end users.

---

## 6. Open Items & Future Polish

* **Unattended Scheduler Run:** Observe the scheduler automatically trigger upcoming daily runs without manual intervention (`airflow dags test`).
* **Model File Swapping:** Connect the `promote_champion` stub to perform actual `.joblib` file replacements on disk.
* **Airflow Variables Externalization:** Migrate hardcoded DAG strings (S3 bucket names, warehouse names) into Airflow Environment Variables.
* **Local Dashboard Sync:** Update local `streamlit_app/` files to match the new charts built