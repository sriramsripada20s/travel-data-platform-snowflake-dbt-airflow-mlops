from __future__ import annotations

import random
from pathlib import Path

import pandas as pd


TIME_SLOT_POOL = ["09:00", "11:00", "13:00", "15:00", "17:00"]

# How many daily timeslots each category typically runs.
CATEGORY_SLOT_COUNTS = {
    "Theme Park": 4,
    "Attraction": 3,
    "Museum": 3,
    "Cruise": 2,
    "Guided Tour": 2,
    "Food & Drink": 2,
    "Show": 2,
    "Adventure": 1,
}

SEASONALITY_MULTIPLIER = {
    1: 0.80, 2: 0.80, 3: 0.90, 4: 1.00, 5: 1.05, 6: 1.20,
    7: 1.30, 8: 1.30, 9: 1.05, 10: 0.95, 11: 0.90, 12: 1.15,
}

WEEKEND_PRICE_MULTIPLIER = 1.15  # milder than the demand-side weekend effect


def generate_availability(
    experiences: pd.DataFrame,
    start_date: str,
    end_date: str,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate availability rows for every ACTIVE experience across the
    date range. Inactive experiences get no availability at all.

    Slot times are picked once per experience (deterministic given seed +
    experience_id) rather than re-randomized every day, so the same
    experience always runs at the same times.
    """
    date_range = pd.date_range(start_date, end_date, freq="D")
    rows = []

    for _, exp in experiences.iterrows():
        if not exp["active_flag"]:
            continue

        n_slots = CATEGORY_SLOT_COUNTS.get(exp["category"], 2)
        slot_rng = random.Random(f"{seed}_{exp['experience_id']}_slots")
        slot_times = slot_rng.sample(
            TIME_SLOT_POOL, k=min(n_slots, len(TIME_SLOT_POOL))
        )
        per_slot_capacity = max(1, int(exp["capacity"]) // len(slot_times))

        for date in date_range:
            month = date.month
            is_weekend = date.weekday() >= 5
            season_mult = SEASONALITY_MULTIPLIER.get(month, 1.0)
            weekend_mult = WEEKEND_PRICE_MULTIPLIER if is_weekend else 1.0
            price = round(exp["base_price"] * season_mult * weekend_mult, 2)

            for slot in slot_times:
                rows.append(
                    {
                        "experience_id": exp["experience_id"],
                        "experience_date": date.date(),
                        "time_slot": slot,
                        "total_capacity": per_slot_capacity,
                        "available_capacity": per_slot_capacity,
                        "price": price,
                    }
                )

    return pd.DataFrame(rows)


def save_availability(
    df: pd.DataFrame,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    suppliers = pd.read_csv("data/generated/clean/suppliers.csv")
    experiences = pd.read_csv("data/generated/clean/experiences.csv")

    availability = generate_availability(
        experiences,
        start_date="2025-09-01",
        end_date="2026-08-31",
        seed=42,
    )

    save_availability(
        availability,
        "data/generated/clean/availability.csv",
    )

    print(availability.head())
    print(f"Generated {len(availability):,} availability rows.")
    print(f"Covers {availability['experience_id'].nunique()} experiences.")