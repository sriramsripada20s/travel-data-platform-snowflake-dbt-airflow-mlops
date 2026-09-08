from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd


SEASONALITY_MULTIPLIER = {
    1: 0.80, 2: 0.80, 3: 0.90, 4: 1.00, 5: 1.05, 6: 1.20,
    7: 1.30, 8: 1.30, 9: 1.05, 10: 0.95, 11: 0.90, 12: 1.15,
}
WEEKEND_DEMAND_MULTIPLIER = 1.35

# Constant tuning overall booking volume relative to capacity. Raise if too
# many slots come out empty; lower if slots sell out too fast at dev scale.
DEMAND_SCALE_CONSTANT = 1.0

HIGH_CANCEL_CATEGORIES = {"Adventure", "Cruise"}
LOW_CANCEL_CATEGORIES = {"Museum", "Attraction"}

BASE_CANCELLATION_RATE = 0.10


def _base_popularity(experience_id: str, seed: int) -> float:
    """Deterministic per-experience popularity draw (lognormal, right-skewed).
    Not stored on the experiences table — recomputed from a seeded RNG keyed
    by experience_id so it's stable across runs without a schema change."""
    rng = random.Random(f"{seed}_popularity_{experience_id}")
    return rng.lognormvariate(0, 0.6)


def _price_elasticity_factor(price: float, base_price: float) -> float:
    if base_price <= 0:
        return 1.0
    ratio = price / base_price
    return max(0.3, 1.4 - 0.6 * ratio)


def _rating_factor(rating: float) -> float:
    if rating >= 4.5:
        return 1.15
    if rating < 4.0:
        return 0.85
    return 1.0


def _cancellation_multiplier(
    lead_time_days: int,
    discount_pct: float,
    channel: str,
    category: str,
    prior_cancellations: int,
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


def generate_bookings(
    customers: pd.DataFrame,
    experiences: pd.DataFrame,
    availability: pd.DataFrame,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate bookings against availability slots, implementing the
    demand and cancellation logic from docs/business_rules.md.

    Returns (bookings_df, updated_availability_df) — available_capacity is
    decremented by guests booked against each slot, capped at 0.

    Two-pass design:
      Pass 1 — for each availability slot, sample expected demand, generate
        booking skeletons up to that slot's capacity.
      Pass 2 — process bookings in chronological order per customer,
        computing cancellation probability from lead time / discount /
        channel / category / the customer's *prior* cancellation count
        (only meaningful with chronological ordering).
    """
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    exp_lookup = experiences.set_index("experience_id")
    customer_ids = customers["customer_id"].tolist()

    availability = availability.copy()
    booking_rows: list[dict] = []
    booking_counter = 1

    for idx, row in availability.iterrows():
        exp = exp_lookup.loc[row["experience_id"]]
        date = pd.Timestamp(row["experience_date"])
        month = date.month
        is_weekend = date.weekday() >= 5

        popularity = _base_popularity(row["experience_id"], seed)
        season_mult = SEASONALITY_MULTIPLIER.get(month, 1.0)
        weekend_mult = WEEKEND_DEMAND_MULTIPLIER if is_weekend else 1.0
        price_factor = _price_elasticity_factor(row["price"], exp["base_price"])
        rating_factor = _rating_factor(exp["rating"])

        expected_bookings = (
            popularity * season_mult * weekend_mult * price_factor
            * rating_factor * DEMAND_SCALE_CONSTANT
        )
        n_bookings = min(
            int(np_rng.poisson(max(0.0, expected_bookings))),
            row["total_capacity"],
        )

        capacity_used = 0
        for _ in range(n_bookings):
            guests = rng.choices([1, 2, 3, 4], weights=[0.45, 0.35, 0.15, 0.05])[0]
            if capacity_used + guests > row["total_capacity"]:
                break
            capacity_used += guests

            lead_bucket = rng.choices(
                ["short", "medium", "long"], weights=[0.4, 0.4, 0.2]
            )[0]
            if lead_bucket == "short":
                lead_days = rng.randint(1, 7)
            elif lead_bucket == "medium":
                lead_days = rng.randint(8, 30)
            else:
                lead_days = rng.randint(31, 120)

            booking_timestamp = (
                date
                - pd.Timedelta(days=lead_days)
                + pd.Timedelta(hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
            )

            has_discount = rng.random() < 0.30
            discount_pct = rng.uniform(0.05, 0.30) if has_discount else 0.0
            ticket_price = row["price"]
            gross = ticket_price * guests
            discount_amount = round(gross * discount_pct, 2)
            booking_amount = max(0.0, round(gross - discount_amount, 2))

            channel = rng.choices(
                ["MOBILE", "WEB", "PARTNER"], weights=[0.55, 0.35, 0.10]
            )[0]

            booking_rows.append(
                {
                    "booking_id": f"B{90000 + booking_counter}",
                    "customer_id": rng.choice(customer_ids),
                    "experience_id": row["experience_id"],
                    "booking_timestamp": booking_timestamp,
                    "experience_date": row["experience_date"],
                    "number_of_guests": guests,
                    "ticket_price": ticket_price,
                    "discount_amount": discount_amount,
                    "booking_amount": booking_amount,
                    "booking_channel": channel,
                    "currency": "USD",
                    "lead_time_days": lead_days,
                    "discount_pct": round(discount_pct, 4),
                    "category": exp["category"],
                }
            )
            booking_counter += 1

        availability.loc[idx, "available_capacity"] = max(
            0, row["total_capacity"] - capacity_used
        )

    bookings_df = pd.DataFrame(booking_rows)

    if bookings_df.empty:
        bookings_df["booking_status"] = []
        bookings_df["payment_status"] = []
        return bookings_df, availability

    bookings_df = bookings_df.sort_values(
        ["customer_id", "booking_timestamp"]
    ).reset_index(drop=True)

    prior_cancellations: dict[str, int] = {}
    statuses = []
    payment_statuses = []

    for _, b in bookings_df.iterrows():
        prior = prior_cancellations.get(b["customer_id"], 0)
        mult = _cancellation_multiplier(
            lead_time_days=b["lead_time_days"],
            discount_pct=b["discount_pct"],
            channel=b["booking_channel"],
            category=b["category"],
            prior_cancellations=prior,
        )
        prob = min(0.85, max(0.02, BASE_CANCELLATION_RATE * mult))
        cancelled = rng.random() < prob

        if cancelled:
            prior_cancellations[b["customer_id"]] = prior + 1
            status = "REFUNDED" if rng.random() < 0.33 else "CANCELLED"
        else:
            status = "CONFIRMED"

        statuses.append(status)
        payment_statuses.append(
            rng.choices(["PAID", "PENDING", "FAILED"], weights=[0.90, 0.05, 0.05])[0]
        )

    bookings_df["booking_status"] = statuses
    bookings_df["payment_status"] = payment_statuses
    bookings_df = bookings_df.drop(columns=["category"])

    return bookings_df, availability


def save_bookings(df: pd.DataFrame, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    customers = pd.read_csv("data/generated/clean/customers.csv")
    experiences = pd.read_csv("data/generated/clean/experiences.csv")
    availability = pd.read_csv("data/generated/clean/availability.csv")

    bookings, updated_availability = generate_bookings(
        customers, experiences, availability, seed=42
    )

    save_bookings(bookings, "data/generated/clean/bookings.csv")
    save_bookings(updated_availability, "data/generated/clean/availability.csv")

    print(bookings.head())
    print(f"\nGenerated {len(bookings):,} bookings.")
    print(bookings["booking_status"].value_counts(normalize=True))