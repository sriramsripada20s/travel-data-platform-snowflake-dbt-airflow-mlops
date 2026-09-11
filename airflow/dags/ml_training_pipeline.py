"""
Travel Experience Platform -- WEEKLY ML training DAG.

Split out from the daily ingestion DAG deliberately: with only ~200 new
bookings/day, retraining daily gives each run a negligible new increment
to learn from -- not worth the compute. Weekly gives a meaningfully
larger accumulation (~1,400 new bookings) between retrains.

NOT Asset-triggered off the daily DAG's ML_FEATURES_ASSET, even though
that Asset exists (declared as an outlet in the daily DAG) -- Assets fire
on EVERY update, which would mean daily triggering again, defeating the
point of this split. A plain weekly cron is the correct mechanism for
"wait for N days' accumulation," not an Asset dependency. This DAG simply
queries the feature table fresh each time it runs; no direct coupling to
the daily DAG's run status is needed.
"""

from __future__ import annotations

import datetime as dt

# TaskFlow API decorators and core DAG imports
from airflow.sdk import dag, task

# Airflow Connection ID for Slack alerting
SLACK_CONN_ID = "slack_default"


# ============================================================================
# FAILURE CALLBACK & ALERTING
# ============================================================================
def _on_dag_failure(context: dict) -> None:
    """
    FAILURE HANDLING:
    Fires instantly if any task in the retraining pipeline fails, sending a Slack
    alert with task, DAG, and execution date details.
    """
    from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

    task_id = context["task_instance"].task_id
    dag_id = context["dag"].dag_id
    exec_date = context["ds"]
    SlackWebhookHook(slack_webhook_conn_id=SLACK_CONN_ID).send(
        text=f":rotating_light: *{dag_id}* failed on task `{task_id}` for {exec_date}."
    )


# ============================================================================
# MASTER WEEKLY ML TRAINING DAG
# ============================================================================
@dag(
    dag_id="ml_training_pipeline",
    description="train -> evaluate -> promote/keep -> predict -> summary (weekly)",
    schedule="0 6 * * 1",  # Every Monday at 06:00 UTC (after weekend daily loads land)
    start_date=dt.datetime(2026, 9, 15),  # First Monday after ingestion baseline
    catchup=False,  # NO BACKFILLS: Skipping a week retrains on accumulated data, not historical runs
    max_active_runs=1,  # Ensures only one retraining run executes at a time
    default_args={
        "retries": 1,
        "retry_delay": dt.timedelta(minutes=10),
        "on_failure_callback": _on_dag_failure,
    },
    tags=["travel-platform", "weekly", "ml"],
)
def ml_training_pipeline():

    # ------------------------------------------------------------------------
    # STEP 1: MODEL RETRAINING & HOLDOUT EVALUATION
    # ------------------------------------------------------------------------
    @task
    def train_model() -> dict:
        """
        Loads updated feature matrices from Snowflake (MARTS.ML_DEMAND_FEATURES),
        applies time-based train/test splits, and trains candidate regression models.
        Returns MAE and evaluation metrics via XCom.
        """
        import sys
        sys.path.insert(0, "/opt/airflow/ml")
        from data_loader import drop_insufficient_history, load_demand_features, time_based_split
        from train_models import encode_features, train_and_evaluate_all

        # Load fresh feature store dataset from Snowflake
        df = load_demand_features()
        df = drop_insufficient_history(df)
        
        # Chronological train/test split (prevents lookahead leakage)
        train_df, test_df = time_based_split(df)
        X_train, X_test = encode_features(train_df, test_df)
        y_train = train_df["target_bookings"].reset_index(drop=True)
        y_test = test_df["target_bookings"].reset_index(drop=True)

        # Train Ridge, XGBoost, and Random Forest candidates
        _, results = train_and_evaluate_all(X_train, y_train, X_test, y_test)
        print(f"Trained on {len(train_df):,} rows, tested on {len(test_df):,} rows.")
        
        return {"results": results}  # Passed to evaluate_model via XCom

    # ------------------------------------------------------------------------
    # STEP 2: CHAMPION VS. CHALLENGER EVALUATION GATE
    # ------------------------------------------------------------------------
    @task
    def evaluate_model(train_output: dict) -> dict:
        """
        Identifies the top-performing candidate model (lowest MAE) and compares its
        score against the active Champion model listed in registry.json.
        """
        import json
        from pathlib import Path

        results = train_output["results"]
        best = min(results, key=lambda r: r["mae"])

        # Inspect current Champion model MAE from registry.json
        registry_path = Path("/opt/airflow/models/registry.json")
        current_champion_mae = None
        if registry_path.exists():
            registry = json.loads(registry_path.read_text())
            champion_name = registry.get("champion")
            for entry in registry.get("models", []):
                if entry["model_name"] == champion_name:
                    current_champion_mae = entry["mae"]

        # Promotion threshold: Candidate must strictly beat current Champion MAE
        should_promote = current_champion_mae is None or best["mae"] < current_champion_mae
        return {
            "should_promote": should_promote,
            "candidate_name": best["model"],
            "candidate_mae": best["mae"],
            "current_champion_mae": current_champion_mae,
        }

    # ------------------------------------------------------------------------
    # STEP 3: CONDITIONAL BRANCHING
    # ------------------------------------------------------------------------
    @task.branch
    def decide_promotion(evaluation: dict) -> str:
        """
        BRANCHING OPERATOR:
        Dynamically routes execution to 'promote_champion' or 'keep_current_champion'
        based on the evaluation result.
        """
        return "promote_champion" if evaluation["should_promote"] else "keep_current_champion"

    @task
    def promote_champion(evaluation: dict) -> None:
        """Executes when challenger model beats current champion MAE."""
        print(f"Promoting {evaluation['candidate_name']} "
              f"(MAE {evaluation['candidate_mae']} beats "
              f"current champion MAE {evaluation['current_champion_mae']})")

    @task
    def keep_current_champion(evaluation: dict) -> None:
        """Executes when challenger fails to improve upon champion MAE."""
        print(f"Keeping current champion (MAE {evaluation['current_champion_mae']} "
              f"beat candidate MAE {evaluation['candidate_mae']})")

    # ------------------------------------------------------------------------
    # STEP 4: BATCH INFERENCE & SLACK REPORTING
    # ------------------------------------------------------------------------
    @task(trigger_rule="none_failed_min_one_success")
    # TRIGGER RULE: Ensures execution runs after EITHER branch completes
    def generate_predictions() -> None:
        """Generates future demand forecasts using the current champion model."""
        print("Scoring upcoming dates with the current champion model.")

    @task(trigger_rule="all_done")
    # TRIGGER RULE: Fires summary alert to Slack regardless of branch outcome
    def send_summary(evaluation: dict) -> None:
        """Posts weekly MLOps retraining summary metrics to Slack."""
        from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

        SlackWebhookHook(slack_webhook_conn_id=SLACK_CONN_ID).send(
            text=(f":brain: Weekly retrain complete. Candidate "
                  f"{evaluation['candidate_name']} (MAE {evaluation['candidate_mae']}) "
                  f"vs. champion (MAE {evaluation['current_champion_mae']}). "
                  f"Promoted: {evaluation['should_promote']}")
        )

    # ============================================================================
    # PIPELINE TASK GRAPH WIRING
    # ============================================================================
    
    # Task flow initialization
    trained = train_model()
    evaluation = evaluate_model(trained)
    branch = decide_promotion(evaluation)

    promoted = promote_champion(evaluation)
    kept = keep_current_champion(evaluation)
    predictions = generate_predictions()
    summary = send_summary(evaluation)

    # Dependency mapping & Branch resolution
    branch >> [promoted, kept] >> predictions >> summary


# Instantiate the DAG
ml_training_pipeline()