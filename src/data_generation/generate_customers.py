from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
from faker import Faker


COUNTRY_WEIGHTS = {
    "USA": 0.30,
    "UK": 0.18,
    "Germany": 0.14,
    "France": 0.10,
    "India": 0.10,
    "UAE": 0.08,
    "Other": 0.10,
}

COUNTRY_LANGUAGE = {
    "USA": "English",
    "UK": "English",
    "Germany": "German",
    "France": "French",
    "India": "English",
    "UAE": "Arabic",
    "Other": "English",
}

ACQUISITION_CHANNEL_WEIGHTS = {
    "Organic": 0.30,
    "Google Ads": 0.22,
    "Meta Ads": 0.18,
    "Affiliate": 0.12,
    "Email": 0.10,
    "Direct": 0.08,
}

SEGMENT_WEIGHTS_ESTABLISHED = {
    "New": 0.20,
    "Repeat": 0.45,
    "VIP": 0.15,
    "Dormant": 0.20,
}
SEGMENT_WEIGHTS_RECENT = {
    "New": 0.90,
    "Repeat": 0.10,
}


def _weighted_choice(options: dict[str, float]) -> str:
    labels = list(options.keys())
    weights = list(options.values())
    return random.choices(labels, weights=weights, k=1)[0]


def _segment_for_signup(signup_date, reference_date) -> str:
    """Customers signed up within the last 90 days can only be New/Repeat;
    older customers draw from the full segment distribution."""
    tenure_days = (reference_date - signup_date).days
    if tenure_days < 90:
        return _weighted_choice(SEGMENT_WEIGHTS_RECENT)
    return _weighted_choice(SEGMENT_WEIGHTS_ESTABLISHED)


def generate_customers(
    num_customers: int,
    seed: int = 42,
    start_date: str = "-3y",
    end_date: str = "today",
) -> pd.DataFrame:
    """Generate clean customer master data.

    customer_segment is derived from signup_date's tenure, not sampled
    independently, so a customer who just signed up can't be Dormant.
    """
    random.seed(seed)
    Faker.seed(seed)
    fake = Faker()

    reference_date = fake.date_between(start_date="today", end_date="today")

    rows = []

    for i in range(1, num_customers + 1):
        customer_id = f"C{10000 + i}"
        country = _weighted_choice(COUNTRY_WEIGHTS)
        signup_date = fake.date_between(start_date=start_date, end_date=end_date)

        rows.append(
            {
                "customer_id": customer_id,
                "signup_date": signup_date,
                "country": country,
                "preferred_language": COUNTRY_LANGUAGE[country],
                "acquisition_channel": _weighted_choice(ACQUISITION_CHANNEL_WEIGHTS),
                "customer_segment": _segment_for_signup(signup_date, reference_date),
            }
        )

    return pd.DataFrame(rows)


def save_customers(
    df: pd.DataFrame,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    customers = generate_customers(num_customers=2000, seed=42)

    save_customers(
        customers,
        "data/generated/clean/customers.csv",
    )

    print(customers.head())
    print(f"Generated {len(customers):,} customers.")
    print(customers["country"].value_counts(normalize=True))
    print(customers["customer_segment"].value_counts(normalize=True))