# Phase 2 — Loading Raw Data into Snowflake (via AWS S3)

## 📌 Executive Summary
The primary goal of Phase 2 is to land the raw, deliberately dirty CSV files generated in Phase 1 into a Snowflake `RAW` landing schema. 

By keeping raw tables loosely typed and preserving all injected anomalies (duplicate keys, null values, negative amounts, out-of-order timestamps), we establish a true enterprise ingestion layer. Phase 3's dbt staging models will clean, deduplicate, and validate this data.

---

## 🏗️ Architecture & Authentication Flow
┌─────────────────┐       ┌─────────────────┐       ┌────────────────────────┐
│   Phase 1 CSVs  │ ────► │  AWS S3 Bucket  │ ────► │ Snowflake Storage Integ│
│ (Raw Local Data)│       │ (raw/*.csv)     │       │  (AWS IAM Role Trust)  │
└─────────────────┘       └─────────────────┘       └───────────┬────────────┘
│
▼
┌─────────────────┐       ┌─────────────────┐       ┌────────────────────────┐
│  Snowflake RAW  │ ◄──── │  COPY INTO Command      │  External Stage        │
│  Landing Tables │       │ (ON_ERROR=CONTINUE)    │  (@RAW_STAGE)          │
└─────────────────┘       └─────────────────┘       └────────────────────────┘

## 🚀 Execution Steps

### Step 1: AWS Setup (S3 & IAM Role)
* Created S3 bucket: `s3://travel-experience-platform`
* Configured IAM policy (`SnowflakeS3AccessPolicy`) scoping bucket access to:
  * `s3:ListBucket`
  * `s3:GetBucketLocation`
  * `s3:GetObject`
  * `s3:GetObjectVersion`
* Created IAM role (`SnowflakeS3AccessRole_new`) with a temporary deny-all trust policy until Snowflake identity details were generated.

### Step 2: Snowflake Infrastructure Setup
* **Warehouse:** `TRAVEL_WH` (X-Small, Auto-suspend)
* **Database:** `TRAVEL_PLATFORM`
* **Schema:** `RAW`
* **File Format:** `CSV_STANDARD`
  * Skips header row (`SKIP_HEADER = 1`)
  * Supports field quoting (`FIELD_OPTIONALLY_ENCLOSED_BY = '"'`)
  * Converts empty fields to `NULL` (`NULL_IF = ('', 'NULL', 'null')`)

### Step 3: Storage Integration & IAM Handshake
* Created storage integration in Snowflake: `TRAVEL_S3_INTEGRATION` pointing to `SnowflakeS3AccessRole_new`.
* Ran `DESC STORAGE INTEGRATION TRAVEL_S3_INTEGRATION` to extract Snowflake's generated identity:
  * `STORAGE_AWS_IAM_USER_ARN`
  * `STORAGE_AWS_EXTERNAL_ID`
* Updated the AWS IAM Role Trust Relationship with these credentials, completing secure keyless access between AWS and Snowflake.

### Step 4: External Stage & Data Upload
* Created external stage: `RAW_STAGE` referencing `s3://travel-experience-platform/raw/`.
* Uploaded all 6 Phase 1 CSV files to the `raw/` root folder.
* Verified stage connectivity using `LIST @RAW_STAGE;`.

### Step 5: Table DDL & `COPY INTO` Data Loading
* Created 6 `RAW_*` landing tables matching `data_contracts.md`.
* Configured column definitions to be loosely typed (permissive nullability) to prevent landing failures on dirty raw rows.
* Executed `COPY INTO` commands using `ON_ERROR = 'CONTINUE'` to allow valid dirty data (e.g., duplicate IDs or negative amounts) while catching genuine parsing failures.

---

## 📊 Final Loaded Row Counts

Verified using `SELECT COUNT(*)` across all Snowflake RAW tables.

| Table Name | Raw S3 File | Snowflake Row Count | Ingestion Status |
| :--- | :--- | ---: | :--- |
| `RAW_SUPPLIERS` | `suppliers.csv` | **30** | ✅ Exact Match |
| `RAW_EXPERIENCES` | `experiences.csv` | **120** | ✅ Exact Match |
| `RAW_CUSTOMERS` | `customers.csv` | **12,000** | ✅ Exact Match |
| `RAW_AVAILABILITY` | `availability.csv` | **101,835** | ✅ Exact Match |
| `RAW_BOOKINGS` | `bookings.csv` | **101,149** | ✅ Exact Match (Includes 202 duplicates) |
| `RAW_WEB_EVENTS` | `web_events.csv` | **1,501,433** | ✅ Exact Match (Includes 1,433 duplicates) |

*All row counts exactly match local synthetic CSV outputs, confirming zero row loss during ingestion.*

---

## ⚠️ Issues Encountered & Resolution Strategy

### Issue 1: `LIST @RAW_STAGE/suppliers/` Returned Empty
* **Root Cause:** `COPY INTO` commands were pointed at subdirectories (`@RAW_STAGE/suppliers/`), but files were uploaded flat at the `raw/` root (`raw/suppliers.csv`).
* **Fix:** Updated `COPY INTO` file paths to target flat CSV filenames directly (`@RAW_STAGE/suppliers.csv`).

### Issue 2: Cross-Platform Shell Syntax (PowerShell vs. Bash)
* **Root Cause:** Bash inline environment variable declaration (`SCALE_FACTOR=0.3 python -m ...`) failed in PowerShell.
* **Fix:** Standardized PowerShell environment setup:
  ```powershell
  $env:SCALE_FACTOR="0.3"
  python -m src.data_generation.generator