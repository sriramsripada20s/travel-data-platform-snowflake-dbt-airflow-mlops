from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
from faker import Faker


SUPPLIER_TYPES = [
    "Tour Operator",
    "Attraction",
    "Museum",
    "Theme Park",
    "Cruise Operator",
    "Activity Provider",
]

COUNTRIES = [
    "Italy",
    "France",
    "United Kingdom",
    "United Arab Emirates",
    "Spain",
]

STATUSES = ["ACTIVE", "INACTIVE"]


def generate_suppliers(
    num_suppliers: int,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate clean supplier master data."""
    random.seed(seed)
    Faker.seed(seed)
    fake = Faker()

    rows = []

    for i in range(1, num_suppliers + 1):
        supplier_id = f"SUP{i:05d}"

        rows.append(
            {
                "supplier_id": supplier_id,
                "supplier_name": f"{fake.company()} Experiences",
                "country": random.choice(COUNTRIES),
                "supplier_type": random.choice(SUPPLIER_TYPES),
                "contract_start_date": fake.date_between(
                    start_date="-4y",
                    end_date="-30d",
                ),
                "commission_rate": round(random.uniform(0.10, 0.30), 4),
                "supplier_status": random.choices(
                    STATUSES,
                    weights=[0.95, 0.05],
                    k=1,
                )[0],
            }
        )

    return pd.DataFrame(rows)


def save_suppliers(
    df: pd.DataFrame,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    suppliers = generate_suppliers(num_suppliers=100, seed=42)

    save_suppliers(
        suppliers,
        "data/generated/clean/suppliers.csv",
    )

    print(suppliers.head())
    print(f"Generated {len(suppliers):,} suppliers.")
