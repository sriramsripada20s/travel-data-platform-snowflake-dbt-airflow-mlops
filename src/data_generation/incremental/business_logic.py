"""
Shared demand and cancellation logic for the incremental generator.

Extracted here because generate_incremental.py and backfill_availability_gap.py
both need the EXACT same formulas -- these constants must match what
generate_bookings.py/generate_availability.py (the batch generator) use, so
incremental data stays statistically consistent with the historical
backfill. Having ONE place to update these, instead of several inline
copies, is what stops them drifting out of sync silently.

If you ever retune DEMAND_SCALE_CONSTANT or BASE_CANCELLATION_RATE in the
batch generator again, update it here too.
"""

from __future__ import annotations

import random

SEASONALITY_MULTIPLIER = {
    1: 0.80, 2: 0.80, 3: 0.90, 4: 1.00, 5: 1.05, 6: 1.20,
    7: 1.30, 8: 1.30, 9: 1.05, 10: 0.95, 11: 0.90, 12: 1.15,
}
WEEKEND_DEMAND_MULTIPLIER = 1.35
WEEKEND_PRICE_MULTIPLIER = 1.15
DEMAND_SCALE_CONSTANT = 0.75

HIGH_CANCEL_CATEGORIES = {"Adventure", "Cruise"}
LOW_CANCEL_CATEGORIES = {"Museum", "Attraction"}
BASE_CANCELLATION_RATE = 0.10

TIME_SLOT_POOL = ["09:00", "11:00", "13:00", "15:00", "17:00"]
CATEGORY_SLOT_COUNTS = {
    "Theme Park": 4, "Attraction": 3, "Museum": 3, "Cruise": 2,
    "Guided Tour": 2, "Food & Drink": 2, "Show": 2, "Adventure": 1,
}


def base_popularity(experience_id: str, seed: int = 42) -> float:
    rng = random.Random(f"{seed}_popularity_{experience_id}")
    return rng.lognormvariate(0, 0.6)


def price_elasticity_factor(price: float, base_price: float) -> float:
    if base_price <= 0:
        return 1.0
    ratio = price / base_price
    return max(0.3, 1.4 - 0.6 * ratio)


def rating_factor(rating: float) -> float:
    if rating >= 4.5:
        return 1.15
    if rating < 4.0:
        return 0.85
    return 1.0


def cancellation_multiplier(
    lead_time_days: int, discount_pct: float, channel: str,
    category: str, prior_cancellations: int,
) -> float:
    mult = 1.0
    if lead_time_days > 60:
        mult *= 1.6
    elif lead_time_days >= 14:
        mult *= 1.2
    elif lead_time_days < 3:
        mult *= 0.5
    if discount_pct > 0.20:
        mult *= 1.3
    if channel == "PARTNER":
        mult *= 1.25
    if category in HIGH_CANCEL_CATEGORIES:
        mult *= 1.3
    elif category in LOW_CANCEL_CATEGORIES:
        mult *= 0.85
    if prior_cancellations == 1:
        mult *= 1.4
    elif prior_cancellations >= 2:
        mult *= 1.9
    return mult


def sample_lead_time_days(rng: random.Random) -> int:
    bucket = rng.choices(["short", "medium", "long"], weights=[0.4, 0.4, 0.2])[0]
    if bucket == "short":
        return rng.randint(1, 7)
    if bucket == "medium":
        return rng.randint(8, 30)
    return rng.randint(31, 120)