from __future__ import annotations

import random
from pathlib import Path

import pandas as pd


FUNNEL_DROPOFF = {
    "after_search": 0.38,
    "after_view": 0.44,
    "after_availability_check": 0.49,
    "after_add_to_cart": 0.28,
    "after_checkout": 0.27,
}

DEVICE_TYPE_WEIGHTS = {"mobile": 0.60, "desktop": 0.32, "tablet": 0.08}

TRAFFIC_SOURCE_WEIGHTS = {
    "organic": 0.30,
    "google_ads": 0.22,
    "meta_ads": 0.18,
    "affiliate": 0.12,
    "email": 0.10,
    "direct": 0.08,
}

DROPOFF_STAGES = [
    ("SEARCH", None),
    ("VIEW_EXPERIENCE", "after_search"),
    ("CHECK_AVAILABILITY", "after_view"),
    ("ADD_TO_CART", "after_availability_check"),
    ("CHECKOUT", "after_add_to_cart"),
]

# Overall event budget: keeps total web_events roughly between 1M and 1.5M
# regardless of SCALE_FACTOR. Converting sessions (one per real booking,
# always 6 events) get first claim on the budget; whatever's left funds
# non-converting sessions. This replaces a fixed session-count cap, which
# would behave inconsistently as SCALE_FACTOR grows (a fixed session cap
# is a shrinking share of total events at larger scale).
MAX_TOTAL_EVENTS = 1_500_000

# Absolute safety ceiling on non-converting sessions, independent of the
# event budget above — mainly guards a pathological edge case (e.g.
# bookings=0, which would make the budget-implied target huge) rather
# than mattering in normal use.
MAX_NON_CONVERTING_SESSIONS = 2_000_000


def _weighted_choice(rng: random.Random, options: dict[str, float]) -> str:
    labels = list(options.keys())
    weights = list(options.values())
    return rng.choices(labels, weights=weights, k=1)[0]


def _overall_conversion_rate() -> float:
    rate = 1.0
    for key in FUNNEL_DROPOFF.values():
        rate *= 1 - key
    return rate


def _expected_dropoff_session_length() -> float:
    """Expected number of events in a non-converting session, derived
    exactly from FUNNEL_DROPOFF's survival probabilities (not an empirical
    guess) — SEARCH always happens, then each later stage's probability of
    being reached is the product of surviving every prior drop-off."""
    survival = 1.0
    expected = 1.0  # SEARCH always included
    for key in ["after_search", "after_view", "after_availability_check", "after_add_to_cart"]:
        survival *= 1 - FUNNEL_DROPOFF[key]
        expected += survival
    return expected


def _session_timestamps(start: pd.Timestamp, n_events: int, rng: random.Random) -> list[pd.Timestamp]:
    times = [start]
    for _ in range(n_events - 1):
        times.append(times[-1] + pd.Timedelta(minutes=rng.randint(1, 20)))
    return times


def _generate_converting_session(
    booking: pd.Series,
    exp_lookup: pd.DataFrame,
    session_id: str,
    event_id_start: int,
    rng: random.Random,
) -> list[dict]:
    exp = exp_lookup.loc[booking["experience_id"]]
    stages = ["SEARCH", "VIEW_EXPERIENCE", "CHECK_AVAILABILITY", "ADD_TO_CART", "CHECKOUT", "PURCHASE"]

    purchase_time = pd.Timestamp(booking["booking_timestamp"])
    gaps = [rng.randint(1, 20) for _ in range(len(stages) - 1)]
    total_gap = sum(gaps)
    start = purchase_time - pd.Timedelta(minutes=total_gap)
    timestamps = _session_timestamps(start, len(stages), rng)
    timestamps[-1] = purchase_time

    device_type = _weighted_choice(rng, DEVICE_TYPE_WEIGHTS)
    traffic_source = _weighted_choice(rng, TRAFFIC_SOURCE_WEIGHTS)

    events = []
    for i, stage in enumerate(stages):
        events.append(
            {
                "event_id": f"EVT{event_id_start + i:07d}",
                "customer_id": booking["customer_id"],
                "session_id": session_id,
                "experience_id": None if stage == "SEARCH" else booking["experience_id"],
                "event_timestamp": timestamps[i],
                "event_type": stage,
                "device_type": device_type,
                "traffic_source": traffic_source,
                "city_searched": exp["city"],
            }
        )
    return events


def _generate_dropoff_session(
    customer_id: str,
    experience_id: str,
    city: str,
    start_time: pd.Timestamp,
    session_id: str,
    event_id_start: int,
    rng: random.Random,
) -> list[dict]:
    device_type = _weighted_choice(rng, DEVICE_TYPE_WEIGHTS)
    traffic_source = _weighted_choice(rng, TRAFFIC_SOURCE_WEIGHTS)

    included_stages = []
    for stage_name, dropoff_key in DROPOFF_STAGES:
        if dropoff_key is not None and rng.random() < FUNNEL_DROPOFF[dropoff_key]:
            break
        included_stages.append(stage_name)

    timestamps = _session_timestamps(start_time, len(included_stages), rng)

    events = []
    for i, stage in enumerate(included_stages):
        events.append(
            {
                "event_id": f"EVT{event_id_start + i:07d}",
                "customer_id": customer_id,
                "session_id": session_id,
                "experience_id": None if stage == "SEARCH" else experience_id,
                "event_timestamp": timestamps[i],
                "event_type": stage,
                "device_type": device_type,
                "traffic_source": traffic_source,
                "city_searched": city,
            }
        )
    return events


def generate_web_events(
    customers: pd.DataFrame,
    experiences: pd.DataFrame,
    bookings: pd.DataFrame,
    seed: int = 42,
    start_date: str = "2025-09-01",
    end_date: str = "2026-08-31",
    max_total_events: int = MAX_TOTAL_EVENTS,
    max_non_converting_sessions: int | None = MAX_NON_CONVERTING_SESSIONS,
) -> pd.DataFrame:
    rng = random.Random(seed)
    exp_lookup = experiences.set_index("experience_id")
    customer_ids = customers["customer_id"].tolist()
    experience_ids = experiences["experience_id"].tolist()
    experience_cities = experiences.set_index("experience_id")["city"].to_dict()

    all_events: list[dict] = []
    event_counter = 1
    session_counter = 1

    for _, booking in bookings.iterrows():
        session_id = f"SESSION_{session_counter}"
        events = _generate_converting_session(
            booking, exp_lookup, session_id, event_counter, rng
        )
        all_events.extend(events)
        event_counter += len(events)
        session_counter += 1

    conversion_rate = _overall_conversion_rate()
    funnel_implied_target = round(len(bookings) * (1 / conversion_rate - 1))

    converting_events = len(bookings) * 6  # every converting session has all 6 stages
    remaining_event_budget = max(0, max_total_events - converting_events)
    avg_dropoff_length = _expected_dropoff_session_length()
    budget_implied_target = (
        int(remaining_event_budget / avg_dropoff_length) if avg_dropoff_length > 0 else 0
    )

    target_non_converting = funnel_implied_target
    if max_non_converting_sessions is not None:
        target_non_converting = min(target_non_converting, max_non_converting_sessions)
    target_non_converting = min(target_non_converting, budget_implied_target)

    date_range = pd.date_range(start_date, end_date, freq="D")

    for _ in range(target_non_converting):
        customer_id = rng.choice(customer_ids)
        experience_id = rng.choice(experience_ids)
        city = experience_cities[experience_id]
        random_date = rng.choice(date_range)
        start_time = pd.Timestamp(random_date) + pd.Timedelta(
            hours=rng.randint(6, 23), minutes=rng.randint(0, 59)
        )

        session_id = f"SESSION_{session_counter}"
        events = _generate_dropoff_session(
            customer_id, experience_id, city, start_time, session_id, event_counter, rng
        )
        all_events.extend(events)
        event_counter += len(events)
        session_counter += 1

    return pd.DataFrame(all_events)


def save_web_events(df: pd.DataFrame, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    customers = pd.read_csv("data/generated/clean/customers.csv")
    experiences = pd.read_csv("data/generated/clean/experiences.csv")
    bookings = pd.read_csv("data/generated/clean/bookings.csv")

    web_events = generate_web_events(customers, experiences, bookings, seed=42)

    save_web_events(web_events, "data/generated/clean/web_events.csv")

    print(web_events.head())
    print(f"\nGenerated {len(web_events):,} web events across {web_events['session_id'].nunique():,} sessions.")
    print("\nEvent type distribution:")
    print(web_events["event_type"].value_counts(normalize=True))
    purchase_sessions = web_events.loc[web_events["event_type"] == "PURCHASE", "session_id"].nunique()
    print(f"\nSessions ending in PURCHASE: {purchase_sessions:,} (should equal booking count: {len(bookings):,})")