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

from airflow.sdk import dag, task

SLACK_CONN_ID = "slack_default"


def _on_dag_failure(context: dict) -> None:
    from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

    task_id = context["task_instance"].task_id
    dag_id = context["dag"].dag_id
    exec_date = context["ds"]
    SlackWebhookHook(slack_webhook_conn_id=SLACK_CONN_ID).send(
        text=f":rotating_light: *{dag_id}* failed on task `{task_id}` for {exec_date}."
    )


@dag(
    dag_id="ml_training_pipeline",
    description="train -> evaluate -> promote/keep -> predict -> summary (weekly)",
    schedule="0 6 * * 1",  # every Monday at 06:00 -- runs after the
                           # weekend's daily ingestion has already landed
    start_date=dt.datetime(2026, 9, 15),  # first Monday after ingestion begins
    catchup=False,  # no reason to backfill missed WEEKLY training runs the
                     # way we backfill missed daily data -- a skipped
                     # week's retrain just means next Monday trains on two
                     # weeks' accumulation instead of one.
    max_active_runs=1,
    default_args={
        "retries": 1,
        "retry_delay": dt.timedelta(minutes=10),
        "on_failure_callback": _on_dag_failure,
    },
    tags=["travel-platform", "weekly", "ml"],
)
def ml_training_pipeline():

    @task
    def train_model() -> dict:
        import sys
        sys.path.insert(0, "/opt/airflow/ml")
        from data_loader import drop_insufficient_history, load_demand_features, time_based_split
        from train_models import encode_features, train_and_evaluate_all

        df = load_demand_features()
        df = drop_insufficient_history(df)
        train_df, test_df = time_based_split(df)
        X_train, X_test = encode_features(train_df, test_df)
        y_train = train_df["target_bookings"].reset_index(drop=True)
        y_test = test_df["target_bookings"].reset_index(drop=True)

        _, results = train_and_evaluate_all(X_train, y_train, X_test, y_test)
        print(f"Trained on {len(train_df):,} rows, tested on {len(test_df):,} rows.")
        return {"results": results}

    @task
    def evaluate_model(train_output: dict) -> dict:
        import json
        from pathlib import Path

        results = train_output["results"]
        best = min(results, key=lambda r: r["mae"])

        registry_path = Path("/opt/airflow/models/registry.json")
        current_champion_mae = None
        if registry_path.exists():
            registry = json.loads(registry_path.read_text())
            champion_name = registry.get("champion")
            for entry in registry.get("models", []):
                if entry["model_name"] == champion_name:
                    current_champion_mae = entry["mae"]

        should_promote = current_champion_mae is None or best["mae"] < current_champion_mae
        return {
            "should_promote": should_promote,
            "candidate_name": best["model"],
            "candidate_mae": best["mae"],
            "current_champion_mae": current_champion_mae,
        }

    @task.branch
    def decide_promotion(evaluation: dict) -> str:
        return "promote_champion" if evaluation["should_promote"] else "keep_current_champion"

    @task
    def promote_champion(evaluation: dict) -> None:
        print(f"Promoting {evaluation['candidate_name']} "
              f"(MAE {evaluation['candidate_mae']} beats "
              f"current champion MAE {evaluation['current_champion_mae']})")

    @task
    def keep_current_champion(evaluation: dict) -> None:
        print(f"Keeping current champion (MAE {evaluation['current_champion_mae']} "
              f"beat candidate MAE {evaluation['candidate_mae']})")

    @task(trigger_rule="none_failed_min_one_success")
    def generate_predictions() -> None:
        print("Scoring upcoming dates with the current champion model.")

    @task(trigger_rule="all_done")
    def send_summary(evaluation: dict) -> None:
        from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

        SlackWebhookHook(slack_webhook_conn_id=SLACK_CONN_ID).send(
            text=(f":brain: Weekly retrain complete. Candidate "
                  f"{evaluation['candidate_name']} (MAE {evaluation['candidate_mae']}) "
                  f"vs. champion (MAE {evaluation['current_champion_mae']}). "
                  f"Promoted: {evaluation['should_promote']}")
        )

    trained = train_model()
    evaluation = evaluate_model(trained)
    branch = decide_promotion(evaluation)

    promoted = promote_champion(evaluation)
    kept = keep_current_champion(evaluation)
    predictions = generate_predictions()
    summary = send_summary(evaluation)

    branch >> [promoted, kept] >> predictions >> summary


ml_training_pipeline()