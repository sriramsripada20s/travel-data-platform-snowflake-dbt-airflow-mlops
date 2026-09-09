"""
ONE-TIME script. Opens availability for the next 120 days in bulk, closing
the gap left by the old +365-day logic. Run once, then use
generate_incremental.py going forward.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from generate_incremental import (
    load_day_to_snowflake,
    open_new_availability_day,
    upload_day_to_s3,
)
from snowflake_conn import get_connection
from state import get_active_experiences, get_last_generated_date

REPO_ROOT = Path(__file__).resolve().parents[3]
INCREMENTAL_OUTPUT_DIR = REPO_ROOT / "data" / "generated" / "incremental"

BACKFILL_WINDOW_DAYS = 120


def run_backfill() -> None:
    conn = get_connection()
    last_date = get_last_generated_date()
    experiences = get_active_experiences()
    start_date = last_date + dt.timedelta(days=1)

    for offset in range(BACKFILL_WINDOW_DAYS):
        target_date = start_date + dt.timedelta(days=offset)
        availability_df = open_new_availability_day(conn, experiences, target_date, seed=42)

        out_dir = INCREMENTAL_OUTPUT_DIR / f"dt={target_date.isoformat()}"
        out_dir.mkdir(parents=True, exist_ok=True)
        availability_df.to_csv(out_dir / "availability.csv", index=False)
        print(f"{target_date}: opened {len(availability_df)} availability rows")

    print(f"\nUploading and loading {BACKFILL_WINDOW_DAYS} days...")
    for offset in range(BACKFILL_WINDOW_DAYS):
        target_date = start_date + dt.timedelta(days=offset)
        out_dir = INCREMENTAL_OUTPUT_DIR / f"dt={target_date.isoformat()}"
        upload_day_to_s3(target_date, out_dir)

    for offset in range(BACKFILL_WINDOW_DAYS):
        target_date = start_date + dt.timedelta(days=offset)
        load_day_to_snowflake(conn, target_date)

    print(f"\nBackfill complete: availability open through "
          f"{start_date + dt.timedelta(days=BACKFILL_WINDOW_DAYS - 1)}.")


if __name__ == "__main__":
    run_backfill()