from __future__ import annotations

import decimal
import pandas as pd

# Custom module to retrieve secure Snowflake database connection
from config import get_connection

# Define feature schema specifications for machine learning pipelines
NUMERIC_FEATURE_COLUMNS = [
    "capacity", "rating", "base_price", "avg_price",
    "bookings_prev_1d", "bookings_prev_7d_avg", "bookings_prev_28d_avg",
    "utilization_prev_7d_avg", "cancellation_rate_prev_28d_avg",
    "days_of_prior_history", "is_weekend",
]
CATEGORICAL_FEATURE_COLUMNS = ["city", "category", "day_name", "month", "quarter"]
TARGET_COLUMN = "target_bookings"


def load_demand_features() -> pd.DataFrame:
    """
    Extracts feature store records from Snowflake's ML_DEMAND_FEATURES model.
    
    Data Hygiene Steps:
    1. Lowercases column names for consistent Pandas indexing.
    2. Central Decimal-to-Float Conversion: Automatically casts Snowflake 
       NUMBER/DECIMAL types to Python floats to prevent downstream XGBoost/NumPy math crashes.
    3. Converts feature_date strings to Pandas datetime objects for temporal operations.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM ML.ML_DEMAND_FEATURES")
        columns = [c[0].lower() for c in cur.description]
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=columns)
    finally:
        cur.close()

    # Cast Snowflake Decimal types to float across all columns
    for col in df.columns:
        if df[col].map(lambda x: isinstance(x, decimal.Decimal)).any():
            df[col] = df[col].astype(float)

    # Standardize date column formatting
    df["feature_date"] = pd.to_datetime(df["feature_date"])
    if "is_weekend" in df.columns:
        df["is_weekend"] = df["is_weekend"].astype(int)
    return df


def drop_insufficient_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes early "cold-start" rows where 7-day or 28-day rolling window features 
    are NULL due to insufficient historical dates.
    
    Guarantees that downstream model training algorithms (like XGBoost or Random Forest)
    receive fully populated time-series features.
    """
    required = ["bookings_prev_7d_avg", "bookings_prev_28d_avg"]
    before = len(df)
    df = df.dropna(subset=required)
    after = len(df)
    print(f"Dropped {before - after:,} rows with insufficient rolling history "
          f"({before:,} -> {after:,} rows).")
    return df

def time_based_split(df: pd.DataFrame, test_days: int = 60) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits the dataset chronologically into Training and Testing sets.
    
    IMPORTANT MACHINE LEARNING GUARDRAIL:
    Never use random train-test splitting (e.g., train_test_split) on time-series data!
    Random splitting causes data leakage by allowing future data points into past training.
    
    This function uses a strict cutoff date:
    - Train Set: Everything on or before cutoff date.
    - Test Set: The final `test_days` (default 60 days) to simulate real-world evaluation.
    """
    cutoff = df["feature_date"].max() - pd.Timedelta(days=test_days)
    train = df[df["feature_date"] <= cutoff].copy()
    test = df[df["feature_date"] > cutoff].copy()
    print(f"Split at {cutoff.date()}: train={len(train):,} rows, test={len(test):,} rows.")
    return train, test


# ============================================================================
# SCRIPT EXECUTION & VERIFICATION
# ============================================================================
if __name__ == "__main__":
    # 1. Fetch raw features from Snowflake
    df = load_demand_features()
    print(f"Loaded {len(df):,} rows.")
    
    # 2. Filter out cold-start nulls
    df = drop_insufficient_history(df)
    
    # 3. Perform temporal train-test split
    train_df, test_df = time_based_split(df)
    
    # 4. Display sample training records
    print("\nSample Training Data Head:")
    print(train_df[["experience_id", "feature_date", "target_bookings"]].head())