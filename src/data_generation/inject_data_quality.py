from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd


DQ_RATES = {
    "duplicate_booking_pct": 0.002,
    "null_customer_id_pct": 0.001,
    "negative_booking_amount_pct": 0.0005,
    "invalid_experience_fk_pct": 0.0005,
    "duplicate_event_pct": 0.002,
    "out_of_order_event_timestamp_pct": 0.001,
    "late_arriving_booking_pct": 0.001,
}


def _sample_indices(df: pd.DataFrame, pct: float, rng: np.random.Generator) -> np.ndarray:
    n = max(0, round(len(df) * pct))
    n = min(n, len(df))
    if n == 0:
        return np.array([], dtype=int)
    return rng.choice(df.index.to_numpy(), size=n, replace=False)


def inject_booking_defects(
    bookings: pd.DataFrame,
    seed: int = 42,
    rates: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    rates = rates or DQ_RATES
    rng = np.random.default_rng(seed)
    df = bookings.copy()
    report: dict[str, int] = {}

    dup_idx = _sample_indices(df, rates["duplicate_booking_pct"], rng)
    duplicated_rows = df.loc[dup_idx]
    df = pd.concat([df, duplicated_rows], ignore_index=True)
    report["duplicate_booking_rows_added"] = len(duplicated_rows)

    null_cust_idx = _sample_indices(df, rates["null_customer_id_pct"], rng)
    df.loc[null_cust_idx, "customer_id"] = None
    report["null_customer_id_rows"] = len(null_cust_idx)

    neg_amount_idx = _sample_indices(df, rates["negative_booking_amount_pct"], rng)
    df.loc[neg_amount_idx, "booking_amount"] = -df.loc[neg_amount_idx, "booking_amount"].abs()
    report["negative_booking_amount_rows"] = len(neg_amount_idx)

    bad_fk_idx = _sample_indices(df, rates["invalid_experience_fk_pct"], rng)
    df.loc[bad_fk_idx, "experience_id"] = "EXP999999"
    report["invalid_experience_fk_rows"] = len(bad_fk_idx)

    late_idx = _sample_indices(df, rates["late_arriving_booking_pct"], rng)
    exp_dates = pd.to_datetime(df.loc[late_idx, "experience_date"])
    df.loc[late_idx, "booking_timestamp"] = (
        exp_dates + pd.to_timedelta(rng.integers(1, 10, size=len(late_idx)), unit="D")
    ).astype(str)
    report["late_arriving_booking_rows"] = len(late_idx)

    return df, report


def inject_web_event_defects(
    web_events: pd.DataFrame,
    seed: int = 43,
    rates: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    rates = rates or DQ_RATES
    rng = np.random.default_rng(seed)
    df = web_events.copy()
    report: dict[str, int] = {}

    dup_idx = _sample_indices(df, rates["duplicate_event_pct"], rng)
    duplicated_rows = df.loc[dup_idx]
    df = pd.concat([df, duplicated_rows], ignore_index=True)
    report["duplicate_event_rows_added"] = len(duplicated_rows)

    session_ids = df["session_id"].unique()
    n_sessions_to_break = max(0, round(len(session_ids) * rates["out_of_order_event_timestamp_pct"]))
    sessions_to_break = rng.choice(session_ids, size=min(n_sessions_to_break, len(session_ids)), replace=False)

    rows_touched = 0
    for sid in sessions_to_break:
        session_rows = df.index[df["session_id"] == sid].tolist()
        if len(session_rows) < 2:
            continue
        i, j = rng.choice(session_rows, size=2, replace=False)
        df.loc[i, "event_timestamp"], df.loc[j, "event_timestamp"] = (
            df.loc[j, "event_timestamp"],
            df.loc[i, "event_timestamp"],
        )
        rows_touched += 2
    report["out_of_order_sessions_broken"] = len(sessions_to_break)
    report["out_of_order_rows_touched"] = rows_touched

    return df, report


def inject_data_quality(
    clean_dir: str | Path,
    raw_dir: str | Path,
    seed: int = 42,
    rates: dict | None = None,
) -> dict:
    clean_dir = Path(clean_dir)
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    full_report: dict[str, dict] = {}

    for passthrough_name in ["suppliers", "experiences", "customers", "availability"]:
        df = pd.read_csv(clean_dir / f"{passthrough_name}.csv")
        df.to_csv(raw_dir / f"{passthrough_name}.csv", index=False)

    bookings = pd.read_csv(clean_dir / "bookings.csv")
    dirty_bookings, bookings_report = inject_booking_defects(bookings, seed=seed, rates=rates)
    dirty_bookings.to_csv(raw_dir / "bookings.csv", index=False)
    full_report["bookings"] = bookings_report

    web_events = pd.read_csv(clean_dir / "web_events.csv")
    dirty_web_events, events_report = inject_web_event_defects(web_events, seed=seed + 1, rates=rates)
    dirty_web_events.to_csv(raw_dir / "web_events.csv", index=False)
    full_report["web_events"] = events_report

    return full_report


if __name__ == "__main__":
    report = inject_data_quality(
        clean_dir="data/generated/clean",
        raw_dir="data/generated/raw",
        seed=42,
    )

    print("Data quality injection complete. Raw (dirty) copies written to data/generated/raw/\n")
    for dataset, counts in report.items():
        print(f"{dataset}:")
        for key, value in counts.items():
            print(f"  {key}: {value:,}")