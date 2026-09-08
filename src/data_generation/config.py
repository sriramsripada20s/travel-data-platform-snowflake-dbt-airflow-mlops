"""
Central configuration for synthetic data generation.

Counts derive from SCALE_FACTOR so the same generators can produce a
smoke-test dataset, a dev dataset, or the full portfolio dataset without
changing generation logic.

    SCALE_FACTOR = 0.01  -> smoke test
    SCALE_FACTOR = 0.05  -> dev dataset (default)
    SCALE_FACTOR = 1.00  -> full dataset

Override at runtime, e.g.:
    SCALE_FACTOR=0.01 python -m src.data_generation.generate_reference_data
"""

from __future__ import annotations

import os

RANDOM_SEED = int(os.environ.get("RANDOM_SEED", 42))
SCALE_FACTOR = float(os.environ.get("SCALE_FACTOR", 0.05))

START_DATE = "2025-09-01"
END_DATE = "2026-08-31"

# Base counts at SCALE_FACTOR = 1.0 (the full dataset)
BASE_NUM_SUPPLIERS = 100
BASE_NUM_EXPERIENCES = 400
BASE_NUM_CUSTOMERS = 40_000
BASE_NUM_BOOKINGS = 250_000


def _scaled(base: int) -> int:
    return max(1, round(base * SCALE_FACTOR))


NUM_SUPPLIERS = _scaled(BASE_NUM_SUPPLIERS)
NUM_EXPERIENCES = _scaled(BASE_NUM_EXPERIENCES)
NUM_CUSTOMERS = _scaled(BASE_NUM_CUSTOMERS)
NUM_BOOKINGS = _scaled(BASE_NUM_BOOKINGS)


if __name__ == "__main__":
    print(f"SCALE_FACTOR    = {SCALE_FACTOR}")
    print(f"RANDOM_SEED     = {RANDOM_SEED}")
    print(f"NUM_SUPPLIERS   = {NUM_SUPPLIERS}")
    print(f"NUM_EXPERIENCES = {NUM_EXPERIENCES}")
    print(f"NUM_CUSTOMERS   = {NUM_CUSTOMERS}")
    print(f"NUM_BOOKINGS    = {NUM_BOOKINGS}")