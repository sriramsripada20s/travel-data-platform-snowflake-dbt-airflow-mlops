"""
Unit tests for ml/data_loader.py's pure-pandas functions.
"""

import pandas as pd
import pytest

from data_loader import drop_insufficient_history, time_based_split


@pytest.fixture
def sample_features_df():
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    return pd.DataFrame({
        "feature_date": dates,
        "experience_id": ["EXP1001"] * 30,
        "bookings_prev_7d_avg": [1.0] * 30,
        "bookings_prev_28d_avg": [1.0] * 30,
        "target_bookings": range(30),
    })

# Verifies that feature rows are split chronologically without shuffling or dropping data.
class TestTimeBasedSplit:
    def test_split_is_chronological_not_random(self, sample_features_df):
        train, test = time_based_split(sample_features_df, test_days=7)
        assert train["feature_date"].max() <= test["feature_date"].min()

    def test_split_preserves_all_rows(self, sample_features_df):
        train, test = time_based_split(sample_features_df, test_days=7)
        assert len(train) + len(test) == len(sample_features_df)

    def test_test_set_covers_requested_window(self, sample_features_df):
        train, test = time_based_split(sample_features_df, test_days=7)
        max_date = sample_features_df["feature_date"].max()
        expected_cutoff = max_date - pd.Timedelta(days=7)
        assert train["feature_date"].max() <= expected_cutoff
        assert test["feature_date"].min() > expected_cutoff

# Confirms rows with missing required history fields are removed before model training.
class TestDropInsufficientHistory:
    def test_drops_rows_with_null_required_columns(self):
        df = pd.DataFrame({
            "bookings_prev_7d_avg": [1.0, None, 2.0],
            "bookings_prev_28d_avg": [1.0, 2.0, None],
            "other_col": ["a", "b", "c"],
        })
        result = drop_insufficient_history(df)
        assert len(result) == 1
        assert result.iloc[0]["other_col"] == "a"

    def test_keeps_all_rows_when_none_are_missing(self):
        df = pd.DataFrame({
            "bookings_prev_7d_avg": [1.0, 2.0, 3.0],
            "bookings_prev_28d_avg": [1.0, 2.0, 3.0],
        })
        result = drop_insufficient_history(df)
        assert len(result) == 3