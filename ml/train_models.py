"""
Trains three genuinely different regression algorithms on ml_demand_features,
evaluates all on the same held-out test set, saves each, and marks the
best-performing one as the "champion" -- the stable filename other code
(a batch-prediction script, later Airflow) should always point at, regardless
of which algorithm happens to win on any given training run.

Algorithms, deliberately chosen to differ in kind, not just tree-vs-tree:
  - XGBoost        (gradient boosting)
  - Random Forest  (bagging)
  - Ridge           (linear)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from xgboost import XGBRegressor

from data_loader import (
    CATEGORICAL_FEATURE_COLUMNS,
    NUMERIC_FEATURE_COLUMNS,
    TARGET_COLUMN,
    drop_insufficient_history,
    load_demand_features,
    time_based_split,
)
from evaluate import evaluate, print_comparison

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"
REGISTRY_PATH = MODELS_DIR / "registry.json"


def impute_numeric_nulls(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    XGBoost handles missing values natively; Ridge and RandomForest do not
    and will error on any NaN. Remaining nulls at this point are legitimate,
    not a bug: bookings_prev_1d is null on an experience's very first day
    (no prior day exists), and cancellation_rate_prev_28d_avg can be null
    when the trailing window had zero bookings to compute a rate from.
    Filled with 0 -- "no prior signal" is a reasonable default for a
    count/rate feature. Printed explicitly so imputation is visible, not
    silent.
    """
    na_counts = df[columns].isna().sum()
    na_counts = na_counts[na_counts > 0]
    if not na_counts.empty:
        print("Imputing missing feature values (filled with 0):")
        print(na_counts.to_string())
    return df[columns].fillna(0)


def encode_features(
    train_df: pd.DataFrame, test_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    One-hot encode categoricals, fit on train's categories only, then align
    test to those exact columns (filling any category test has that train
    didn't with 0). Using train-only categories is deliberate: a model
    should never be encoded against categories it never saw during
    training -- that would be a subtle form of leakage/inconsistency.
    Shared across all three models so the comparison is apples-to-apples.
    """
    train_numeric = impute_numeric_nulls(train_df, NUMERIC_FEATURE_COLUMNS).reset_index(drop=True)
    test_numeric = impute_numeric_nulls(test_df, NUMERIC_FEATURE_COLUMNS).reset_index(drop=True)

    train_cat = pd.get_dummies(
        train_df[CATEGORICAL_FEATURE_COLUMNS].astype(str),
        prefix=CATEGORICAL_FEATURE_COLUMNS,
    ).reset_index(drop=True)
    test_cat = pd.get_dummies(
        test_df[CATEGORICAL_FEATURE_COLUMNS].astype(str),
        prefix=CATEGORICAL_FEATURE_COLUMNS,
    ).reset_index(drop=True)
    test_cat = test_cat.reindex(columns=train_cat.columns, fill_value=0)

    X_train = pd.concat([train_numeric, train_cat], axis=1)
    X_test = pd.concat([test_numeric, test_cat], axis=1)
    return X_train, X_test


def build_models() -> dict:
    return {
        "xgboost": XGBRegressor(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        ),
        "ridge": Ridge(
            alpha=1.0,
            random_state=42,
        ),
    }


def train_and_evaluate_all(
    X_train: pd.DataFrame, y_train: pd.Series,
    X_test: pd.DataFrame, y_test: pd.Series,
) -> tuple[dict, list[dict]]:
    models = build_models()
    fitted_models = {}
    results = []

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = pd.Series(model.predict(X_test), index=y_test.index).clip(lower=0)
        results.append(evaluate(y_test, y_pred, name))
        fitted_models[name] = model

    return fitted_models, results


def save_models_and_registry(fitted_models: dict, results: list[dict]) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    results_by_model = {r["model"]: r for r in results}
    champion_name = min(results, key=lambda r: r["mae"])["model"]
    trained_at = datetime.now(timezone.utc).isoformat()

    registry_entries = []
    for name, model in fitted_models.items():
        file_path = MODELS_DIR / f"{name}_demand_forecast.joblib"
        joblib.dump(model, file_path)

        registry_entries.append({
            "model_name": name,
            "file_path": str(file_path.relative_to(REPO_ROOT)),
            "mae": results_by_model[name]["mae"],
            "rmse": results_by_model[name]["rmse"],
            "n_test_rows": results_by_model[name]["n"],
            "trained_at": trained_at,
            "is_champion": name == champion_name,
        })

    champion_path = MODELS_DIR / "champion_demand_forecast.joblib"
    joblib.dump(fitted_models[champion_name], champion_path)

    with open(REGISTRY_PATH, "w") as f:
        json.dump({
            "champion": champion_name,
            "champion_stable_path": str(champion_path.relative_to(REPO_ROOT)),
            "trained_at": trained_at,
            "models": registry_entries,
        }, f, indent=2)

    print(f"\nChampion: {champion_name} (MAE={results_by_model[champion_name]['mae']})")
    print(f"Saved to: {champion_path}")
    print(f"Registry: {REGISTRY_PATH}")


if __name__ == "__main__":
    df = load_demand_features()
    df = drop_insufficient_history(df)
    train_df, test_df = time_based_split(df)

    X_train, X_test = encode_features(train_df, test_df)
    y_train = train_df[TARGET_COLUMN].reset_index(drop=True)
    y_test = test_df[TARGET_COLUMN].reset_index(drop=True)

    fitted_models, results = train_and_evaluate_all(X_train, y_train, X_test, y_test)

    print()
    print_comparison(results)

    save_models_and_registry(fitted_models, results)