"""
Generates ONE day's data -- availability AND bookings/events for that SAME
day -- exactly like the original batch generator did for the whole year,
just one day at a time. No future-dated availability window, no rolling
buffer: day D's bookings check capacity against D's OWN availability,
created moments earlier in this same run.
"""

from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

from business_logic import (
    BASE_CANCELLATION_RATE,
    CATEGORY_SLOT_COUNTS,
    SEASONALITY_MULTIPLIER,
    TIME_SLOT_POOL,
    WEEKEND_DEMAND_MULTIPLIER,
    WEEKEND_PRICE_MULTIPLIER,
    base_popularity,
    cancellation_multiplier,
    price_elasticity_factor,
    rating_factor,
)
from snowflake_conn import get_connection
from state import (
    advance_last_generated_date,
    get_active_experiences,
    get_existing_customer_ids,
    get_last_generated_date,
    get_next_booking_counter,
    get_next_event_counter,
    get_prior_cancellation_counts,
)

DEMAND_SCALE_CONSTANT = 0.75

REPO_ROOT = Path(__file__).resolve().parents[3]
INCREMENTAL_OUTPUT_DIR = REPO_ROOT / "data" / "generated" / "incremental"

BUCKET_NAME = "travel-experience-platform"
S3_INCREMENTAL_PREFIX = "raw_incremental"
TABLE_MAP = {
    "availability": "RAW_AVAILABILITY",
    "bookings": "RAW_BOOKINGS",
    "web_events": "RAW_WEB_EVENTS",
}


def open_availability_for_date(
    experiences: list[dict], target_date: dt.date, seed: int
) -> pd.DataFrame:
    rows = []
    for exp in experiences:
        n_slots = CATEGORY_SLOT_COUNTS.get(exp["category"], 2)
        slot_rng = random.Random(f"{seed}_{exp['experience_id']}_slots")
        slot_times = slot_rng.sample(TIME_SLOT_POOL, k=min(n_slots, len(TIME_SLOT_POOL)))
        per_slot_capacity = max(1, int(exp["capacity"]) // len(slot_times))

        is_weekend = target_date.weekday() >= 5
        season_mult = SEASONALITY_MULTIPLIER.get(target_date.month, 1.0)
        weekend_mult = WEEKEND_PRICE_MULTIPLIER if is_weekend else 1.0
        price = round(exp["base_price"] * season_mult * weekend_mult, 2)

        for slot in slot_times:
            rows.append({
                "experience_id": exp["experience_id"],
                "experience_date": target_date,
                "time_slot": slot,
                "total_capacity": per_slot_capacity,
                "available_capacity": per_slot_capacity,
                "price": price,
            })
    return pd.DataFrame(rows)


def generate_bookings_and_events_for_date(
    experiences: list[dict], availability_df: pd.DataFrame,
    customer_ids: list[str], prior_cancellations: dict,
    target_date: dt.date, booking_counter_start: int,
    event_counter_start: int, seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = random.Random(f"{seed}_{target_date.isoformat()}")
    np_rng = np.random.default_rng(seed)

    exp_lookup = {e["experience_id"]: e for e in experiences}
    booking_rows = []
    event_rows = []
    booking_counter = booking_counter_start
    event_counter = event_counter_start

    is_weekend = target_date.weekday() >= 5
    season_mult = SEASONALITY_MULTIPLIER.get(target_date.month, 1.0)
    weekend_mult = WEEKEND_DEMAND_MULTIPLIER if is_weekend else 1.0

    for _, slot_row in availability_df.iterrows():
        exp = exp_lookup[slot_row["experience_id"]]
        popularity = base_popularity(exp["experience_id"], seed)
        price_factor = price_elasticity_factor(slot_row["price"], exp["base_price"])
        rate_factor = rating_factor(exp["rating"])

        expected_bookings = (
            popularity * season_mult * weekend_mult * price_factor
            * rate_factor * DEMAND_SCALE_CONSTANT
        )
        n_bookings = min(
            int(np_rng.poisson(max(0.0, expected_bookings))),
            slot_row["total_capacity"],
        )

        capacity_used = 0
        for _ in range(n_bookings):
            guests = rng.choices([1, 2, 3, 4], weights=[0.45, 0.35, 0.15, 0.05])[0]
            if capacity_used + guests > slot_row["total_capacity"]:
                break
            capacity_used += guests

            lead_days = rng.choices(
                [rng.randint(1, 7), rng.randint(8, 30), rng.randint(31, 120)],
                weights=[0.4, 0.4, 0.2],
            )[0]
            booking_timestamp = (
                dt.datetime.combine(target_date, dt.time(rng.randint(0, 23), rng.randint(0, 59)))
                - dt.timedelta(days=lead_days)
            )

            has_discount = rng.random() < 0.30
            discount_pct = rng.uniform(0.05, 0.30) if has_discount else 0.0
            gross = slot_row["price"] * guests
            discount_amount = round(gross * discount_pct, 2)
            booking_amount = max(0.0, round(gross - discount_amount, 2))

            channel = rng.choices(["MOBILE", "WEB", "PARTNER"], weights=[0.55, 0.35, 0.10])[0]
            customer_id = rng.choice(customer_ids)

            prior = prior_cancellations.get(customer_id, 0)
            mult = cancellation_multiplier(lead_days, discount_pct, channel, exp["category"], prior)
            prob = min(0.85, max(0.02, BASE_CANCELLATION_RATE * mult))
            cancelled = rng.random() < prob
            if cancelled:
                prior_cancellations[customer_id] = prior + 1
                status = "REFUNDED" if rng.random() < 0.33 else "CANCELLED"
            else:
                status = "CONFIRMED"
            payment_status = rng.choices(["PAID", "PENDING", "FAILED"], weights=[0.90, 0.05, 0.05])[0]

            booking_rows.append({
                "booking_id": f"B{90000 + booking_counter}",
                "customer_id": customer_id,
                "experience_id": exp["experience_id"],
                "booking_timestamp": booking_timestamp,
                "experience_date": target_date,
                "number_of_guests": guests,
                "ticket_price": slot_row["price"],
                "discount_amount": discount_amount,
                "booking_amount": booking_amount,
                "booking_channel": channel,
                "currency": "USD",
                "lead_time_days": lead_days,
                "discount_pct": round(discount_pct, 4),
                "booking_status": status,
                "payment_status": payment_status,
            })

            stages = ["SEARCH", "VIEW_EXPERIENCE", "CHECK_AVAILABILITY", "ADD_TO_CART", "CHECKOUT", "PURCHASE"]
            gaps = [rng.randint(1, 20) for _ in range(len(stages) - 1)]
            start = booking_timestamp - dt.timedelta(minutes=sum(gaps))
            device_type = rng.choices(["mobile", "desktop", "tablet"], weights=[0.60, 0.32, 0.08])[0]
            traffic_source = rng.choices(
                ["organic", "google_ads", "meta_ads", "affiliate", "email", "direct"],
                weights=[0.30, 0.22, 0.18, 0.12, 0.10, 0.08],
            )[0]
            session_id = f"SESSION_INC_{booking_counter}"
            t = start
            for i, stage in enumerate(stages):
                event_rows.append({
                    "event_id": f"EVT{1_000_000 + event_counter}",
                    "customer_id": customer_id,
                    "session_id": session_id,
                    "experience_id": None if stage == "SEARCH" else exp["experience_id"],
                    "event_timestamp": booking_timestamp if i == len(stages) - 1 else t,
                    "event_type": stage,
                    "device_type": device_type,
                    "traffic_source": traffic_source,
                    "city_searched": exp["city"],
                })
                event_counter += 1
                t += dt.timedelta(minutes=rng.randint(1, 20))

            booking_counter += 1

    return pd.DataFrame(booking_rows), pd.DataFrame(event_rows)


def upload_day_to_s3(target_date: dt.date, out_dir: Path) -> None:
    s3 = boto3.client("s3")
    day_str = target_date.isoformat()
    for table_key in TABLE_MAP:
        filename = f"{table_key}.csv"
        local_path = out_dir / filename
        if not local_path.exists():
            print(f"Skipping {filename} -- not found in {out_dir}")
            continue
        s3_key = f"{S3_INCREMENTAL_PREFIX}/dt={day_str}/{table_key}/{filename}"
        s3.upload_file(str(local_path), BUCKET_NAME, s3_key)
        print(f"Uploaded {local_path} -> s3://{BUCKET_NAME}/{s3_key}")


def load_day_to_snowflake(conn, target_date: dt.date) -> None:
    day_str = target_date.isoformat()
    cur = conn.cursor()
    try:
        for table_key, snowflake_table in TABLE_MAP.items():
            stage_path = f"@RAW_INCREMENTAL_STAGE/dt={day_str}/{table_key}/"
            cur.execute(f"""
                COPY INTO {snowflake_table}
                FROM {stage_path}
                FILE_FORMAT = (FORMAT_NAME = CSV_STANDARD)
                ON_ERROR = 'CONTINUE'
            """)
            print(f"{snowflake_table} <- {stage_path}")
            for row in cur.fetchall():
                print(f"  {row}")
    finally:
        cur.close()


def run_daily_cycle() -> None:
    conn = get_connection()

    last_date = get_last_generated_date()
    target_date = last_date + dt.timedelta(days=1)
    print(f"=== Generating day: {target_date} ===")

    experiences = get_active_experiences()
    customer_ids = get_existing_customer_ids()
    prior_cancellations = get_prior_cancellation_counts()
    booking_counter_start = get_next_booking_counter()
    event_counter_start = get_next_event_counter()

    availability_df = open_availability_for_date(experiences, target_date, seed=42)
    bookings_df, events_df = generate_bookings_and_events_for_date(
        experiences, availability_df, customer_ids, prior_cancellations,
        target_date, booking_counter_start, event_counter_start, seed=42,
    )

    out_dir = INCREMENTAL_OUTPUT_DIR / f"dt={target_date.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    availability_df.to_csv(out_dir / "availability.csv", index=False)
    bookings_df.to_csv(out_dir / "bookings.csv", index=False)
    events_df.to_csv(out_dir / "web_events.csv", index=False)

    print(f"Opened {len(availability_df)} availability rows for {target_date}.")
    print(f"Generated {len(bookings_df)} bookings, {len(events_df)} web events.")

    print("\n--- upload to S3 ---")
    upload_day_to_s3(target_date, out_dir)

    print("\n--- load into Snowflake ---")
    load_day_to_snowflake(conn, target_date)

    advance_last_generated_date(target_date)
    print(f"\n=== PIPELINE_STATE advanced to {target_date}. Done. ===")


if __name__ == "__main__":
    run_daily_cycle()