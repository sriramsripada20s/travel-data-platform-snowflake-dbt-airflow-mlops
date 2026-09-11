"""
Travel Experience Platform -- DAILY ingestion + feature-refresh DAG.

Handles: generate -> validate -> load -> dbt (marts + ML features).
ML TRAINING/EVALUATION/PROMOTION lives in its own WEEKLY DAG
(ml_training_pipeline.py) -- retraining daily doesn't make sense yet given
current data volume (~200 new bookings/day); training weekly gives it a
meaningfully larger increment to learn from each time. The weekly DAG
reads the feature table this DAG keeps fresh -- no direct dependency
between the two DAGs needed, since it just queries Snowflake.

DESIGN DECISION: once Airflow owns the schedule, its logical date (ds) is
authoritative for "which day to process" -- NOT PIPELINE_STATE. Querying
PIPELINE_STATE only made sense when a human was manually deciding what to
run next. PIPELINE_STATE is still WRITTEN here (for audit/backward-compat
with any manual runs), but never READ by this DAG.
"""

from __future__ import annotations

import datetime as dt

# Airflow Providers & TaskFlow API Imports
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.sdk import Asset, dag, task

# ============================================================================
# AIRFLOW ASSETS (EVENT-DRIVEN DATA POINTERS)
# ============================================================================
# Assets represent stateful data objects in external systems (Snowflake tables).
# Downstream workflows can schedule off these outlets updating.
RAW_AVAILABILITY_ASSET = Asset("snowflake://TRAVEL_PLATFORM/RAW/RAW_AVAILABILITY")
RAW_BOOKINGS_ASSET = Asset("snowflake://TRAVEL_PLATFORM/RAW/RAW_BOOKINGS")
RAW_WEB_EVENTS_ASSET = Asset("snowflake://TRAVEL_PLATFORM/RAW/RAW_WEB_EVENTS")
ML_FEATURES_ASSET = Asset("snowflake://TRAVEL_PLATFORM/ML/ML_DEMAND_FEATURES")

# Standardized Airflow Connection IDs (configured via Airflow UI/CLI)
SNOWFLAKE_CONN_ID = "snowflake_default"
AWS_CONN_ID = "aws_default"
SLACK_CONN_ID = "slack_default"
BUCKET_NAME = "travel-experience-platform"
S3_INCREMENTAL_PREFIX = "raw_incremental"

# Mapping logic keys to target Snowflake raw table names
TABLE_MAP = {
    "availability": "RAW_AVAILABILITY",
    "bookings": "RAW_BOOKINGS",
    "web_events": "RAW_WEB_EVENTS",
}


# ============================================================================
# GLOBAL FAILURE CALLBACK & ALERTING
# ============================================================================
def _on_dag_failure(context: dict) -> None:
    """
    FAILURE HANDLING + MONITORING:
    Fires instantly the moment any task in the DAG fails, completely independent 
    of send_summary's end-of-run report. Sends a real-time notification to Slack.
    """
    from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

    task_id = context["task_instance"].task_id
    dag_id = context["dag"].dag_id
    exec_date = context["ds"]
    SlackWebhookHook(slack_webhook_conn_id=SLACK_CONN_ID).send(
        text=f":rotating_light: *{dag_id}* failed on task `{task_id}` for {exec_date}."
    )


# ============================================================================
# DAILY INGESTION DAG DEFINITION
# ============================================================================
@dag(
    dag_id="travel_platform_daily_pipeline",
    description="generate -> validate -> load -> dbt (marts + ML features)",
    schedule="@daily",
    start_date=dt.datetime(2026, 9, 9),  # Day AFTER the last verified manual run (2026-09-08)
    catchup=True,  # BACKFILLS: Airflow automatically runs every missed daily interval in sequence
    max_active_runs=1,  # Serial execution constraint: Day D+1 ID counters depend on Day D finishing
    default_args={
        "retries": 2,
        "retry_delay": dt.timedelta(minutes=5),
        "on_failure_callback": _on_dag_failure,
    },
    tags=["travel-platform", "daily", "ingestion"],
)
def travel_platform_daily_pipeline():

    # ------------------------------------------------------------------------
    # STEP 1: DATA GENERATION WITH IDEMPOTENCY GUARD
    # ------------------------------------------------------------------------
    @task
    def generate_data(ds: str = None) -> str:
        """
        SCHEDULING / DATA INTERVALS:
        Airflow's logical execution date (`ds`) serves as the single source of truth 
        for the target date—not a value read from PIPELINE_STATE.
        """
        import sys
        from pathlib import Path

        sys.path.insert(0, "/opt/airflow/src/data_generation/incremental")
        from generate_incremental import (
            generate_bookings_and_events_for_date,
            open_availability_for_date,
        )
        from snowflake_conn import get_connection
        from state import (
            get_active_experiences,
            get_existing_customer_ids,
            get_next_booking_counter,
            get_next_event_counter,
            get_prior_cancellation_counts,
        )

        target_date = dt.date.fromisoformat(ds)

        # IDEMPOTENCY GUARD:
        # Refuses to regenerate a date that's already loaded into Snowflake.
        # Because primary key counters are queried dynamically from Snowflake each run,
        # re-running a date without this check would silently append duplicate rows under new IDs.
        guard_conn = get_connection()
        guard_cur = guard_conn.cursor()
        try:
            guard_cur.execute(
                "SELECT COUNT(*) FROM RAW.RAW_BOOKINGS WHERE experience_date = %(d)s",
                {"d": target_date},
            )
            existing_count = guard_cur.fetchone()[0]
        finally:
            guard_cur.close()

        if existing_count > 0:
            raise ValueError(
                f"{target_date} already has {existing_count} bookings loaded in "
                f"RAW_BOOKINGS. Refusing to regenerate -- re-running would ADD "
                f"duplicate-content rows under new IDs, not overwrite. If this is "
                f"intentional (e.g. cleaning up a bad run), delete the existing "
                f"rows for this date first."
            )

        # Retrieve simulation dependencies from Snowflake state
        experiences = get_active_experiences()
        customer_ids = get_existing_customer_ids()
        prior_cancellations = get_prior_cancellation_counts()
        booking_counter_start = get_next_booking_counter()
        event_counter_start = get_next_event_counter()

        # Generate single-day dataset dataframes
        availability_df = open_availability_for_date(experiences, target_date, seed=42)
        bookings_df, events_df = generate_bookings_and_events_for_date(
            experiences, availability_df, customer_ids, prior_cancellations,
            target_date, booking_counter_start, event_counter_start, seed=42,
        )

        # Persist CSVs to local staging mount
        out_dir = Path(f"/opt/airflow/data/generated/incremental/dt={target_date.isoformat()}")
        out_dir.mkdir(parents=True, exist_ok=True)
        availability_df.to_csv(out_dir / "availability.csv", index=False)
        bookings_df.to_csv(out_dir / "bookings.csv", index=False)
        events_df.to_csv(out_dir / "web_events.csv", index=False)

        print(f"Generated {len(availability_df)} availability rows, "
              f"{len(bookings_df)} bookings, {len(events_df)} web events for {target_date}.")
        return target_date.isoformat()  # Automatically passed via XCom

    # ------------------------------------------------------------------------
    # STEP 2: PRE-UPLOAD DATA-QUALITY GATE
    # ------------------------------------------------------------------------
    @task
    def validate_data(target_date: str) -> str:
        """
        DATA-QUALITY GATE #1 (Pre-Upload Ingestion Guardrail):
        Validates all three generated CSV files (bookings, availability, web_events)
        prior to S3 staging. Raising an assertion error halts execution immediately,
        preventing corrupted data from polluting Snowflake tables.
        """
        import pandas as pd
        from pathlib import Path

        out_dir = Path(f"/opt/airflow/data/generated/incremental/dt={target_date}")

        # 1. Validate Bookings Dataset
        bookings = pd.read_csv(out_dir / "bookings.csv")
        if not bookings.empty:
            assert (bookings["booking_amount"] >= 0).all(), "Negative booking_amount in generated data"
            assert bookings["booking_id"].is_unique, "Duplicate booking_id in generated data"

        # 2. Validate Inventory Availability Dataset
        availability = pd.read_csv(out_dir / "availability.csv")
        if not availability.empty:
            assert (availability["available_capacity"] <= availability["total_capacity"]).all(), \
                "available_capacity exceeds total_capacity in generated data"
            assert (availability["total_capacity"] >= 0).all(), "Negative total_capacity in generated data"

        # 3. Validate Web Clickstream Events Dataset
        web_events = pd.read_csv(out_dir / "web_events.csv")
        if not web_events.empty:
            valid_event_types = {
                "SEARCH", "VIEW_EXPERIENCE", "CHECK_AVAILABILITY",
                "ADD_TO_CART", "CHECKOUT", "PURCHASE",
            }
            assert web_events["event_type"].isin(valid_event_types).all(), \
                "Invalid event_type found in generated data"
            assert web_events["session_id"].notna().all(), "Null session_id found in generated data"

        return target_date

    # ------------------------------------------------------------------------
    # STEP 3: DYNAMIC TASK MAPPING S3 STAGING & DEFERRABLE SENSING
    # ------------------------------------------------------------------------
    @task
    def upload_table_to_s3(target_date: str, table_key: str) -> dict:
        """
        DYNAMIC TASK MAPPING:
        Spawns parallel task instances (one per table key) via .expand().
        S3 Partition Layout: raw_incremental/dt=YYYY-MM-DD/<table>/<table>.csv
        """
        from pathlib import Path

        out_dir = Path(f"/opt/airflow/data/generated/incremental/dt={target_date}")
        local_path = out_dir / f"{table_key}.csv"
        s3_key = f"{S3_INCREMENTAL_PREFIX}/dt={target_date}/{table_key}/{table_key}.csv"

        # CONNECTIONS: Resolved via 'aws_default' connection managed in Airflow
        S3Hook(aws_conn_id=AWS_CONN_ID).load_file(
            filename=str(local_path), key=s3_key, bucket_name=BUCKET_NAME, replace=True,
        )
        return {"table_key": table_key, "s3_key": s3_key, "target_date": target_date}

    @task
    def wait_for_s3_object(upload_result: dict) -> dict:
        """
        SENSOR + DEFERRABLE OPERATOR:
        Confirms object visibility in S3 prior to running COPY INTO.
        Setting deferrable=True releases worker slots to the Triggerer loop while waiting,
        preventing worker thread starvation.
        """
        sensor = S3KeySensor(
            task_id=f"wait_for_{upload_result['table_key']}",
            bucket_name=BUCKET_NAME,
            bucket_key=upload_result["s3_key"],
            aws_conn_id=AWS_CONN_ID,
            deferrable=True,
            timeout=300,
            poke_interval=10,
        )
        sensor.execute(context={})
        return upload_result

    # ------------------------------------------------------------------------
    # STEP 4: APPEND-ONLY SNOWFLAKE INGESTION & STATE AUDIT
    # ------------------------------------------------------------------------
    @task(
        retries=3,  # RETRIES: Network calls to Snowflake receive higher retry limits
        retry_delay=dt.timedelta(minutes=2),
        outlets=[RAW_AVAILABILITY_ASSET, RAW_BOOKINGS_ASSET, RAW_WEB_EVENTS_ASSET],
        # ASSETS: Marks this task as the producer updating these three Airflow Assets
    )
    def load_snowflake_raw(confirmed_upload: dict) -> str:
        """
        Appends S3 partition data into raw Snowflake tables using COPY INTO.
        Snowflake's internal load history prevents loading identical files twice.
        """
        table_key = confirmed_upload["table_key"]
        target_date = confirmed_upload["target_date"]
        snowflake_table = TABLE_MAP[table_key]
        stage_path = f"@RAW_INCREMENTAL_STAGE/dt={target_date}/{table_key}/"

        hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)
        hook.run(f"""
            COPY INTO {snowflake_table}
            FROM {stage_path}
            FILE_FORMAT = (FORMAT_NAME = CSV_STANDARD)
            ON_ERROR = 'CONTINUE'
        """)
        return target_date

    @task
    def update_pipeline_state(target_date: str) -> None:
        """
        Updates RAW.PIPELINE_STATE in Snowflake for manual fallback and audit history.
        Note: The DAG writes to this table, but never reads from it.
        """
        hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)
        hook.run(
            "DELETE FROM RAW.PIPELINE_STATE; "
            f"INSERT INTO RAW.PIPELINE_STATE (last_generated_date, updated_at) "
            f"VALUES ('{target_date}'::DATE, CURRENT_TIMESTAMP())"
        )

    # ------------------------------------------------------------------------
    # STEP 5: TRANSFORMATIONS, DBT TESTING & FEATURE STORE REFRESH
    # ------------------------------------------------------------------------
    @task
    def dbt_build() -> None:
        """
        DATA-QUALITY GATE #2 (Post-Load Data Transformation & Testing):
        Executes all dbt models and data tests across raw, intermediate, and mart layers.
        
        `check=True` ensures that if any dbt test fails (e.g., primary key, 
        not-null, or foreign key mismatches), subprocess.run raises a CalledProcessError,
        halting execution before downstream models or reports are updated.
        """
        import subprocess
        subprocess.run(["dbt", "build"], cwd="/opt/airflow/dbt", check=True)

    @task(outlets=[ML_FEATURES_ASSET])
    def build_ml_features() -> None:
        """
        FEATURE STORE REFRESH:
        Refreshes dbt models under 'models/ml' daily to ensure feature tables 
        stay fresh for consumption by the weekly ML training DAG.
        """
        import subprocess
        subprocess.run(["dbt", "run", "--select", "models/ml"], cwd="/opt/airflow/dbt", check=True)

    # ------------------------------------------------------------------------
    # STEP 6: NOTIFICATIONS & DASHBOARD INTEGRATION
    # ------------------------------------------------------------------------
    @task(trigger_rule="all_done")
    def send_summary(target_date: str) -> None:
        """
        TRIGGER RULE + SLACK ALERTING + STREAMLIT INTEGRATION:
        Fires whether upstream tasks succeed or fail (`all_done`).
        Informs team members that data is fresh for the native Streamlit-in-Snowflake app.
        """
        from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

        dashboard_url = "https://app.snowflake.com/ap-northeast-2.aws/vc93087/#/streamlit-apps/TRAVEL_PLATFORM.MARTS.TRAVEL_DASHBOARD"

        SlackWebhookHook(slack_webhook_conn_id=SLACK_CONN_ID).send(
            text=(f":white_check_mark: Daily ingestion for {target_date} complete. "
                  f"Dashboard is up to date: {dashboard_url}")
        )

    # ============================================================================
    # PIPELINE TASK GRAPH WIRING
    # ============================================================================
    
    # 1. Generation & Quality Check
    generated_date = generate_data()
    validated_date = validate_data(generated_date)

    # 2. Dynamic Parallel Staging, Sensing, Loading
    # .partial() fixes static args (target_date), while .expand() creates mapped task instances per table key
    uploads = upload_table_to_s3.partial(target_date=validated_date).expand(
        table_key=list(TABLE_MAP.keys())
    )
    confirmed = wait_for_s3_object.expand(upload_result=uploads)
    loaded = load_snowflake_raw.expand(confirmed_upload=confirmed)
    state_updated = update_pipeline_state(validated_date)

    # 3. Transformations, Feature Refresh & Slack Reporting
    build = dbt_build()
    features = build_ml_features()
    summary = send_summary(validated_date)

    # Dependency Chain
    loaded >> state_updated >> build >> features >> summary


# Instantiate the DAG
travel_platform_daily_pipeline()