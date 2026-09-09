# Phase 5 — ML Feature Engineering

## Executive Overview
Phase 5 transforms clean, transformed Snowflake tables into a production-ready **Feature Store** (`ML.ML_DEMAND_FEATURES`) for machine learning. The primary objective is to predict daily booking demand per experience while enforcing strict anti-leakage rules.

---

## 1. Pipeline Architecture (`dbt/models/ml/`)

Rather than relying on a single complex SQL query, feature engineering is broken down into a four-stage dbt pipeline where each model has a single, clear responsibility:

┌────────────────────────┐
│    fact_experience_    │ ──► ml_daily_price
│      availability      │     (Aggregates daily dynamic ticket prices)
└────────────────────────┘                  │
▼
┌────────────────────────┐         ┌───────────────────┐
│ int_experience_daily_  │ ──────► │ ml_base_features  │ ◄── dim_date / dim_experience
│        metrics         │         └─────────┬─────────┘     (Joins catalog attributes
└────────────────────────┘                   │                + target ground-truth labels)
▼
┌───────────────────┐
│ml_rolling_features│
└─────────┬─────────┘
│ (Computes lag & moving averages)
▼
┌───────────────────┐
│ml_demand_features │ ◄── Final Feature Store
└───────────────────┘     (Clean passthrough with fixed columns)


| Model | Purpose |
| :--- | :--- |
| **`ml_daily_price`** | Aggregates daily dynamic listing prices per experience from `fact_experience_availability`. |
| **`ml_base_features`** | Merges calendar dimensions (`dim_date`) and static attributes (`dim_experience`) with daily metrics (`int_experience_daily_metrics`). |
| **`ml_rolling_features`** | Computes historical lag features and rolling averages (7-day, 28-day) for demand, utilization, and cancellations. |
| **`ml_demand_features`** | Final, clean feature store model exposed to downstream Python training scripts and Airflow DAGs. |

* **Dataset Grain:** 1 row per experience per date.
* **Dataset Volume:** 41,975 rows at `SCALE_FACTOR = 0.3`.

---

## 2. Core Design Principle: The Anti-Leakage Guardrail

> **Data Leakage Safeguard:**
> Every rolling average and lag feature is computed using:
> `ROWS BETWEEN N PRECEDING AND 1 PRECEDING`
> 
> This explicitly excludes the current row from its own features. If today's actual sales were included in today's features, the model would look artificially accurate in training but fail completely on future dates where today's sales aren't known yet.

### Key Data Safeguards:
* **Target Labels vs. Features:** `target_bookings`, `target_confirmed_bookings`, `target_cancellation_rate`, and `target_utilization_rate` are target labels. They are explicitly documented in `schema.yml` to prevent them from accidentally being used as training inputs.
* **History Tracking:** `days_of_prior_history` counts how many days of prior tracking exist for a given row. This helps downstream scripts filter out "cold-start" periods where rolling averages are incomplete.

---

## 3. Data Contracts & Testing
All four models passed dbt testing alongside the existing project suite:
* **Primary Key Uniqueness:** Composite check on `(experience_id, feature_date)`.
* **Foreign Key Integrity:** Checked against `dim_experience`.
* **Null Safeguards:** Non-null checks on target label columns.
* **Rule Invariants:** Verified `days_of_prior_history >= 0`.