# travel-data-platform-snowflake-dbt-airflow-mlops
# Travel Experience Data & ML Intelligence Platform Using Snowflake, dbt, Airflow, MLOPs

An end-to-end **Data Engineering, Analytics Engineering, Machine Learning, and MLOps project** inspired by modern online travel-experience marketplaces.

The goal of this project is to learn how technologies such as **Python, SQL, Snowflake, dbt, Apache Airflow 3.x, Machine Learning, MLOps, Docker, and Slack** work together by building a realistic data platform rather than learning each tool independently.

---

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

The platform will process marketplace data, build trusted analytical models, generate business KPIs, forecast experience demand, predict booking cancellation risk, and eventually orchestrate the complete lifecycle using Apache Airflow.

---

## Business Problem

A travel marketplace generates data across multiple parts of the customer journey:

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

This project builds the data platform needed to answer those questions.

---

# Architecture

```text
                         DATA SOURCES
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
      Bookings            Web Events         Availability
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                         RAW FILES
                              |
                              v
                         AIRFLOW 3.x
                              |
                      Validate / Ingest
                              |
                              v
                        SNOWFLAKE RAW
                              |
                              v
                             dbt
                              |
                +-------------+-------------+
                |             |             |
                v             v             v
             STAGING     INTERMEDIATE      MARTS
                                             |
                         +-------------------+-------------------+
                         |                                       |
                         v                                       v
                  ANALYTICS MARTS                         ML FEATURES
                                                                 |
                                                                 v
                                                              Python
                                                                 |
                                                          Model Training
                                                                 |
                                                                 v
                                                         Model Evaluation
                                                                 |
                                                                 v
                                                            Predictions
                                                                 |
                                                                 v
                                                             Snowflake
                                                                 |
                                            +--------------------+------------------+
                                            |                                       |
                                            v                                       v
                                       Analytics                              Slack Alerts
```

Future observability layer:

```text
Airflow / Platform Metrics
           |
           v
      Prometheus
           |
           v
        Grafana
```

Future delivery workflow:

```text
GitHub
   |
   v
GitHub Actions
   |
   v
Tests / Validation
   |
   v
CI/CD
```

---

# Technology Stack

| Technology                 | Purpose                                                                   |
| -------------------------- | ------------------------------------------------------------------------- |
| **Python**                 | Synthetic data generation, validation, ML, and utility logic              |
| **SQL**                    | Analytics, transformations, feature engineering, and business logic       |
| **Snowflake**              | Cloud analytical warehouse and compute platform                           |
| **dbt**                    | Data modeling, transformations, testing, documentation, and lineage       |
| **Apache Airflow 3.x**     | Workflow orchestration, scheduling, dependencies, retries, and monitoring |
| **scikit-learn / XGBoost** | Machine-learning model development                                        |
| **MLOps**                  | Model evaluation, versioning, promotion, inference, and monitoring        |
| **Docker**                 | Reproducible local development and runtime environment                    |
| **Slack**                  | Pipeline failure and business alerting                                    |
| **Git / GitHub**           | Version control, documentation, and portfolio hosting                     |
| **Prometheus**             | Platform metrics — later phase                                            |
| **Grafana**                | Operational observability — later phase                                   |
| **GitHub Actions**         | CI/CD and automated validation — later phase                              |

---

# Core Data Domains

The initial platform contains six datasets.

## Customers

**Grain:** One row per customer.

Contains customer registration, location, acquisition, and segmentation attributes.

```text
customer_id
signup_date
country
preferred_language
acquisition_channel
customer_segment
```

---

## Suppliers

**Grain:** One row per supplier.

Represents tour operators, attractions, museums, and other experience providers.

```text
supplier_id
supplier_name
country
supplier_type
contract_start_date
commission_rate
supplier_status
```

---

## Experiences

**Grain:** One row per bookable experience.

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

---

## Bookings

**Grain:** One row per booking.

This is one of the primary transactional datasets.

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
```

---

## Availability & Pricing

**Grain:**

```text
Experience
+
Date
+
Time Slot
```

Tracks inventory, capacity, and pricing.

```text
experience_id
experience_date
time_slot
total_capacity
available_capacity
price
```

---

## Web / App Events

**Grain:** One row per behavioral event.

Example events:

```text
SEARCH
VIEW_EXPERIENCE
CHECK_AVAILABILITY
ADD_TO_CART
CHECKOUT
PURCHASE
```

This dataset will be used to reconstruct the marketplace conversion funnel.

---

# Data Relationships

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

Primary relationships:

```text
bookings.customer_id
    -> customers.customer_id

bookings.experience_id
    -> experiences.experience_id

experiences.supplier_id
    -> suppliers.supplier_id

availability.experience_id
    -> experiences.experience_id

web_events.customer_id
    -> customers.customer_id

web_events.experience_id
    -> experiences.experience_id
```

---

# Synthetic Data

Real marketplace data is proprietary, so the project will generate realistic synthetic data using Python.

The generator will preserve business relationships rather than simply creating independent random rows.

Example customer journey:

```text
Customer C100
     |
     v
SEARCH Rome
     |
     v
VIEW Colosseum
     |
     v
CHECK_AVAILABILITY
     |
     v
ADD_TO_CART
     |
     v
CHECKOUT
     |
     v
PURCHASE
     |
     v
Booking B98231
```

The generated events and booking records will therefore be logically connected.

---

# Dataset Scale

The target full dataset will contain approximately **1.2M–2.3M rows**.

| Dataset      | Target Size |
| ------------ | ----------: |
| Suppliers    |      75–100 |
| Experiences  |     300–500 |
| Customers    |     30K–50K |
| Bookings     |   200K–300K |
| Availability |   250K–500K |
| Web Events   |   750K–1.5M |

The Python generator will support multiple scales.

```python
SCALE_FACTOR = 0.01   # Smoke testing
SCALE_FACTOR = 0.05   # Development
SCALE_FACTOR = 1.00   # Full project
```

This allows the same project to support fast development as well as larger integration and performance runs.

---

# Intentional Data Quality Problems

Production data is rarely perfect.

The synthetic generator will intentionally introduce configurable data-quality issues including:

* Duplicate bookings
* Duplicate event IDs
* Missing customer IDs
* Invalid foreign keys
* Negative booking amounts
* Out-of-order events
* Late-arriving bookings
* Missing input files
* Schema changes

These will later be used to practice:

```text
SQL deduplication
dbt tests
Airflow retries
Airflow failure handling
Data quality gates
Idempotent pipelines
Slack alerting
```

---

# Data Warehouse Model

The analytical layer will use dimensional modeling.

## Booking Model

```text
                         DIM_DATE
                             |
                             |
DIM_CUSTOMER -------- FACT_BOOKINGS -------- DIM_EXPERIENCE
                                             |
                                             |
                                       DIM_SUPPLIER
```

## Behavioral Model

```text
DIM_CUSTOMER
      |
      |
FACT_WEB_EVENTS -------- DIM_EXPERIENCE
      |
      |
   DIM_DATE
```

## Availability Model

```text
DIM_EXPERIENCE
       |
       |
FACT_EXPERIENCE_AVAILABILITY
       |
       |
    DIM_DATE
```

---

# dbt Architecture

Transformations will follow:

```text
RAW
 |
 v
STAGING
 |
 v
INTERMEDIATE
 |
 v
MARTS
```

Example lineage:

```text
RAW_BOOKINGS
      |
      v
STG_BOOKINGS
      |
      v
INT_BOOKING_DETAILS
      |
      v
FACT_BOOKINGS
```

Planned dbt organization:

```text
models/

├── staging/
│   ├── stg_customers.sql
│   ├── stg_suppliers.sql
│   ├── stg_experiences.sql
│   ├── stg_bookings.sql
│   ├── stg_availability.sql
│   └── stg_web_events.sql
│
├── intermediate/
│   ├── int_booking_details.sql
│   ├── int_customer_activity.sql
│   └── int_experience_daily_metrics.sql
│
├── marts/
│   ├── dim_customer.sql
│   ├── dim_supplier.sql
│   ├── dim_experience.sql
│   ├── dim_date.sql
│   ├── fact_bookings.sql
│   ├── fact_web_events.sql
│   └── fact_experience_availability.sql
│
├── analytics/
│   ├── mart_booking_funnel.sql
│   ├── mart_customer_behavior.sql
│   ├── mart_destination_performance.sql
│   └── mart_experience_performance.sql
│
└── ml/
    ├── ml_demand_features.sql
    └── ml_cancellation_features.sql
```

---

# Business KPIs

Initial analytical metrics include:

* Total bookings
* Gross Booking Value / GMV
* Net revenue
* Average booking value
* Cancellation rate
* Booking conversion rate
* Average guests per booking
* Experience utilization
* Repeat customer rate
* Bookings per experience
* Revenue per experience
* Revenue by destination
* Bookings by destination

The analytics layer will be completed before introducing ML so that the underlying business data is validated first.

---

# Machine Learning

## Primary Use Case — Demand Forecasting

Predict:

> How many bookings will each experience receive on a future date?

Prediction grain:

```text
Experience
+
Future Date
```

Potential features:

```text
Previous-day bookings
7-day bookings
28-day bookings
Rolling averages
Day of week
Month
Destination
Experience category
Price
Discount
Capacity
Historical utilization
Booking lead-time behavior
```

Model development will progress through:

```text
Naive Baseline
      |
      v
Rolling Average Baseline
      |
      v
Feature Engineering
      |
      v
XGBoost Regression
      |
      v
Evaluation
      |
      v
Model Selection
      |
      v
Batch Prediction
```

The goal is to demonstrate that the ML model improves on a simple business baseline.

---

## Secondary Use Case — Cancellation Prediction

Later, the platform will predict:

```text
P(booking cancellation)
```

Potential inputs include:

* Booking lead time
* Booking amount
* Discount
* Number of guests
* Destination
* Experience category
* Customer booking history
* Historical cancellations
* Booking channel
* Day of week

This model will provide decision-support information and will not automatically modify customer bookings.

---

# Airflow Orchestration

Once the individual data, analytics, and ML components work independently, Apache Airflow will orchestrate them.

Target workflow:

```text
generate_data
      |
      v
validate_data
      |
      v
load_snowflake_raw
      |
      v
dbt_build
      |
      v
dbt_test
      |
      v
build_ml_features
      |
      v
train_model
      |
      v
evaluate_model
      |
      v
generate_predictions
      |
      v
send_summary
```

Through this workflow, the project will explore Airflow concepts such as:

* DAG design
* TaskFlow API
* Scheduling
* Data intervals
* XCom
* Connections
* Sensors
* Deferrable operators
* Retries
* Trigger rules
* Branching
* Dynamic task mapping
* Assets
* Data-quality gates
* Backfills
* Failure handling
* Monitoring
* Slack alerting

---

# MLOps

After model development, the project will introduce a model lifecycle:

```text
Feature Pipeline
      |
      v
Train Candidate
      |
      v
Evaluate
      |
      v
Performance Gate
     / \
    /   \
 PASS   FAIL
  |       |
  v       v
Register Reject
  |
  v
Batch Inference
  |
  v
Monitor
  |
  v
Retrain
```

The objective is to understand how ML moves from experimentation into a repeatable production workflow.

---

# Project Roadmap

```text
PHASE 0
Business Understanding
Architecture
Data Domains
KPIs
Data Grain
ML Problem Definition
        |
        v
PHASE 1
Synthetic Data Generation
        |
        v
PHASE 2
Snowflake + SQL
        |
        v
PHASE 3
dbt + Dimensional Modeling
        |
        v
PHASE 4
Business Analytics + KPIs
        |
        v
PHASE 5
ML Feature Engineering
        |
        v
PHASE 6
Baseline + Demand Forecasting Model
        |
        v
PHASE 7
Airflow 3.x Orchestration
        |
        v
PHASE 8
MLOps
        |
        v
PHASE 9
Docker / Productionization
        |
        v
PHASE 10
Slack Alerting
```

Later:

```text
Prometheus + Grafana

GitHub Actions + CI/CD
```

Git and GitHub will be used throughout the complete project.

Basic Docker will be introduced when needed to support local Airflow development, with deeper productionization later.

---

# Repository Structure

The repository will gradually evolve toward:

```text
travel-experience-data-platform/

├── airflow/
│   ├── dags/
│   └── tests/
│
├── data/
│   ├── raw/
│   └── generated/
│
├── dbt/
│   ├── models/
│   ├── macros/
│   ├── tests/
│   └── snapshots/
│
├── ml/
│   ├── features/
│   ├── training/
│   ├── evaluation/
│   └── inference/
│
├── src/
│   └── data_generation/
│
├── sql/
│
├── tests/
│
├── docs/
│
├── docker/
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
---

# Learning Objective

This project is not intended to demonstrate a collection of disconnected technologies.

The objective is to understand how business requirements move through the complete data lifecycle:

```text
Business Problem
      |
      v
Source Data
      |
      v
Data Modeling
      |
      v
Warehouse
      |
      v
Transformations
      |
      v
Analytics
      |
      v
ML Features
      |
      v
Machine Learning
      |
      v
Orchestration
      |
      v
MLOps
      |
      v
Monitoring
```

The ultimate goal is to **design, build, orchestrate, and operate a realistic modern Data & ML platform**.

---

