from __future__ import annotations

import pandas as pd


def validate_suppliers(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []

    required = {
        "supplier_id",
        "supplier_name",
        "country",
        "supplier_type",
        "contract_start_date",
        "commission_rate",
        "supplier_status",
    }

    missing = required - set(df.columns)
    if missing:
        errors.append(f"Missing supplier columns: {sorted(missing)}")
        return errors

    if df["supplier_id"].duplicated().any():
        errors.append("supplier_id contains duplicates.")

    if df["supplier_id"].isna().any():
        errors.append("supplier_id contains null values.")

    if not df["commission_rate"].between(0, 1).all():
        errors.append("commission_rate must be between 0 and 1.")

    valid_statuses = {"ACTIVE", "INACTIVE"}
    invalid_statuses = set(df["supplier_status"].dropna()) - valid_statuses
    if invalid_statuses:
        errors.append(
            f"Invalid supplier_status values: {sorted(invalid_statuses)}"
        )

    return errors


def validate_experiences(
    experiences: pd.DataFrame,
    suppliers: pd.DataFrame,
) -> list[str]:
    errors: list[str] = []

    required = {
        "experience_id",
        "experience_name",
        "city",
        "country",
        "category",
        "supplier_id",
        "base_price",
        "capacity",
        "rating",
        "active_flag",
    }

    missing = required - set(experiences.columns)
    if missing:
        errors.append(f"Missing experience columns: {sorted(missing)}")
        return errors

    if experiences["experience_id"].duplicated().any():
        errors.append("experience_id contains duplicates.")

    if experiences["experience_id"].isna().any():
        errors.append("experience_id contains null values.")

    if (experiences["base_price"] <= 0).any():
        errors.append("base_price must be greater than 0.")

    if (experiences["capacity"] <= 0).any():
        errors.append("capacity must be greater than 0.")

    if not experiences["rating"].between(1, 5).all():
        errors.append("rating must be between 1 and 5.")

    valid_suppliers = set(suppliers["supplier_id"])
    invalid_fks = set(experiences["supplier_id"]) - valid_suppliers
    if invalid_fks:
        errors.append(
            f"Invalid supplier_id foreign keys found: "
            f"{len(invalid_fks)} unique values."
        )

    return errors

def validate_customers(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []

    required = {
        "customer_id",
        "signup_date",
        "country",
        "preferred_language",
        "acquisition_channel",
        "customer_segment",
    }

    missing = required - set(df.columns)
    if missing:
        errors.append(f"Missing customer columns: {sorted(missing)}")
        return errors

    if df["customer_id"].duplicated().any():
        errors.append("customer_id contains duplicates.")

    if df["customer_id"].isna().any():
        errors.append("customer_id contains null values.")

    valid_segments = {"New", "Repeat", "VIP", "Dormant"}
    invalid_segments = set(df["customer_segment"].dropna()) - valid_segments
    if invalid_segments:
        errors.append(
            f"Invalid customer_segment values: {sorted(invalid_segments)}"
        )

    if df["signup_date"].isna().any():
        errors.append("signup_date contains null values.")

    return errors


def raise_if_invalid(errors: list[str], dataset_name: str) -> None:
    if errors:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise ValueError(
            f"{dataset_name} validation failed:\n{formatted}"
        )
