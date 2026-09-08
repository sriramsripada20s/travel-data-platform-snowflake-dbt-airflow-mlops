from __future__ import annotations

from pathlib import Path

from .config import NUM_EXPERIENCES, NUM_SUPPLIERS, RANDOM_SEED
from .generate_suppliers import generate_suppliers, save_suppliers
from .generate_experiences import generate_experiences, save_experiences
from .validators import (
    raise_if_invalid,
    validate_experiences,
    validate_suppliers,
)

OUTPUT_DIR = Path("data/generated/clean")


def main() -> None:
    suppliers = generate_suppliers(
        num_suppliers=NUM_SUPPLIERS,
        seed=RANDOM_SEED,
    )

    raise_if_invalid(
        validate_suppliers(suppliers),
        "suppliers",
    )

    experiences = generate_experiences(
        suppliers=suppliers,
        num_experiences=NUM_EXPERIENCES,
        seed=RANDOM_SEED,
    )

    raise_if_invalid(
        validate_experiences(experiences, suppliers),
        "experiences",
    )

    save_suppliers(
        suppliers,
        OUTPUT_DIR / "suppliers.csv",
    )

    save_experiences(
        experiences,
        OUTPUT_DIR / "experiences.csv",
    )

    print("Reference data generation completed successfully.")
    print(f"Suppliers:   {len(suppliers):,}")
    print(f"Experiences: {len(experiences):,}")


if __name__ == "__main__":
    main()