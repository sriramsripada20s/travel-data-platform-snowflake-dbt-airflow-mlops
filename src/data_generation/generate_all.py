from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from .config import (
    END_DATE,
    NUM_CUSTOMERS,
    NUM_EXPERIENCES,
    NUM_SUPPLIERS,
    RANDOM_SEED,
    SCALE_FACTOR,
    START_DATE,
)
from .generate_suppliers import generate_suppliers, save_suppliers
from .generate_experiences import generate_experiences, save_experiences
from .generate_customers import generate_customers, save_customers
from .generate_availability import generate_availability, save_availability
from .generate_bookings import generate_bookings, save_bookings
from .generate_web_events import generate_web_events, save_web_events
from .inject_data_quality import inject_data_quality
from .validators import (
    raise_if_invalid,
    validate_customers,
    validate_experiences,
    validate_suppliers,
)

CLEAN_DIR = Path("data/generated/clean")
RAW_DIR = Path("data/generated/raw")


def main() -> None:
    print(f"Phase 1 — full generation run")
    print(f"SCALE_FACTOR={SCALE_FACTOR}  RANDOM_SEED={RANDOM_SEED}")
    print(f"suppliers={NUM_SUPPLIERS}  experiences={NUM_EXPERIENCES}  customers={NUM_CUSTOMERS}\n")

    t0 = time.time()

    step_start = time.time()
    suppliers = generate_suppliers(num_suppliers=NUM_SUPPLIERS, seed=RANDOM_SEED)
    raise_if_invalid(validate_suppliers(suppliers), "suppliers")
    save_suppliers(suppliers, CLEAN_DIR / "suppliers.csv")
    print(f"[1/7] suppliers:    {len(suppliers):>8,} rows  ({time.time()-step_start:.1f}s)")

    step_start = time.time()
    experiences = generate_experiences(
        suppliers=suppliers, num_experiences=NUM_EXPERIENCES, seed=RANDOM_SEED
    )
    raise_if_invalid(validate_experiences(experiences, suppliers), "experiences")
    save_experiences(experiences, CLEAN_DIR / "experiences.csv")
    print(f"[2/7] experiences:  {len(experiences):>8,} rows  ({time.time()-step_start:.1f}s)")

    step_start = time.time()
    customers = generate_customers(num_customers=NUM_CUSTOMERS, seed=RANDOM_SEED)
    raise_if_invalid(validate_customers(customers), "customers")
    save_customers(customers, CLEAN_DIR / "customers.csv")
    print(f"[3/7] customers:    {len(customers):>8,} rows  ({time.time()-step_start:.1f}s)")

    step_start = time.time()
    availability = generate_availability(
        experiences, start_date=START_DATE, end_date=END_DATE, seed=RANDOM_SEED
    )
    save_availability(availability, CLEAN_DIR / "availability.csv")
    print(f"[4/7] availability: {len(availability):>8,} rows  ({time.time()-step_start:.1f}s)")

    step_start = time.time()
    bookings, availability = generate_bookings(
        customers, experiences, availability, seed=RANDOM_SEED
    )
    save_bookings(bookings, CLEAN_DIR / "bookings.csv")
    save_availability(availability, CLEAN_DIR / "availability.csv")
    print(f"[5/7] bookings:     {len(bookings):>8,} rows  ({time.time()-step_start:.1f}s)")

    step_start = time.time()
    web_events = generate_web_events(customers, experiences, bookings, seed=RANDOM_SEED)
    save_web_events(web_events, CLEAN_DIR / "web_events.csv")
    print(f"[6/7] web_events:   {len(web_events):>8,} rows  ({time.time()-step_start:.1f}s)")

    step_start = time.time()
    dq_report = inject_data_quality(clean_dir=CLEAN_DIR, raw_dir=RAW_DIR, seed=RANDOM_SEED)
    print(f"[7/7] dq injection: done  ({time.time()-step_start:.1f}s)")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Clean data: {CLEAN_DIR}/  Raw (dirty) data: {RAW_DIR}/\n")

    print("Data quality injection summary:")
    for dataset, counts in dq_report.items():
        print(f"  {dataset}:")
        for key, value in counts.items():
            print(f"    {key}: {value:,}")

    print("\nBooking status distribution:")
    print(bookings["booking_status"].value_counts(normalize=True).round(3))

    purchase_sessions = web_events.loc[web_events["event_type"] == "PURCHASE", "session_id"].nunique()
    print(f"\nSanity check — PURCHASE sessions ({purchase_sessions:,}) vs bookings ({len(bookings):,}): "
          f"{'MATCH' if purchase_sessions == len(bookings) else 'MISMATCH — investigate'}")


if __name__ == "__main__":
    main()