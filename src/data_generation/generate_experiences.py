from __future__ import annotations

import random
from pathlib import Path

import pandas as pd


CITY_COUNTRY = {
    "Rome": "Italy",
    "Paris": "France",
    "London": "United Kingdom",
    "Dubai": "United Arab Emirates",
    "Barcelona": "Spain",
}

CITY_WEIGHTS = {
    "Paris": 0.24,
    "Rome": 0.22,
    "London": 0.21,
    "Dubai": 0.19,
    "Barcelona": 0.14,
}

CATEGORIES = {
    "Attraction": {
        "price_range": (25, 120),
        "capacity_range": (100, 1200),
    },
    "Guided Tour": {
        "price_range": (30, 150),
        "capacity_range": (10, 80),
    },
    "Museum": {
        "price_range": (15, 80),
        "capacity_range": (100, 1000),
    },
    "Theme Park": {
        "price_range": (40, 180),
        "capacity_range": (500, 5000),
    },
    "Cruise": {
        "price_range": (35, 250),
        "capacity_range": (50, 600),
    },
    "Food & Drink": {
        "price_range": (25, 140),
        "capacity_range": (10, 100),
    },
    "Adventure": {
        "price_range": (40, 300),
        "capacity_range": (5, 80),
    },
    "Show": {
        "price_range": (25, 200),
        "capacity_range": (50, 2000),
    },
}


def _weighted_city() -> str:
    cities = list(CITY_WEIGHTS.keys())
    weights = list(CITY_WEIGHTS.values())
    #generates a random city based on the weights defined in CITY_WEIGHTS
    return random.choices(cities, weights=weights, k=1)[0]


def _experience_name(city: str, category: str, idx: int) -> str:
    templates = [
        f"{city} {category} Experience",
        f"Best of {city} {category}",
        f"{city} Signature {category}",
        f"Premium {city} {category}",
        f"{city} Highlights {category}",
    ]
    #generates a random experience name based on the city, category, and index
    return f"{random.choice(templates)} #{idx}"


def generate_experiences(
    suppliers: pd.DataFrame,
    num_experiences: int,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate clean experience catalog data linked to valid suppliers."""
    random.seed(seed)

    if suppliers.empty:
        raise ValueError("suppliers DataFrame cannot be empty.")

    active_suppliers = suppliers[
        suppliers["supplier_status"] == "ACTIVE"
    ].copy()

    if active_suppliers.empty:
        raise ValueError("At least one ACTIVE supplier is required.")

    rows = []

    for i in range(1, num_experiences + 1):
        city = _weighted_city()
        country = CITY_COUNTRY[city]
        category = random.choice(list(CATEGORIES.keys()))

        matching_suppliers = active_suppliers[
            active_suppliers["country"] == country
        ]

        supplier_pool = (
            matching_suppliers
            if not matching_suppliers.empty
            else active_suppliers
        )

        supplier_id = random.choice(
            supplier_pool["supplier_id"].tolist()
        )

        price_min, price_max = CATEGORIES[category]["price_range"]
        capacity_min, capacity_max = CATEGORIES[category]["capacity_range"]

        rows.append(
            {
                "experience_id": f"EXP{i:06d}",
                "experience_name": _experience_name(city, category, i),
                "city": city,
                "country": country,
                "category": category,
                "supplier_id": supplier_id,
                "base_price": round(random.uniform(price_min, price_max), 2),
                "capacity": random.randint(capacity_min, capacity_max),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "active_flag": random.choices(
                    [True, False],
                    weights=[0.97, 0.03],
                    k=1,
                )[0],
            }
        )

    return pd.DataFrame(rows)


def save_experiences(
    df: pd.DataFrame,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    suppliers = pd.read_csv(
        "data/generated/clean/suppliers.csv"
    )

    experiences = generate_experiences(
        suppliers=suppliers,
        num_experiences=400,
        seed=42,
    )

    save_experiences(
        experiences,
        "data/generated/clean/experiences.csv",
    )

    print(experiences.head())
    print(f"Generated {len(experiences):,} experiences.")
