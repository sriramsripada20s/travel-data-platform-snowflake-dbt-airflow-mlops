"""
Snowflake connection for the ML training pipeline. Mirrors the pattern in
streamlit_app/connection.py, kept as its own self-contained copy rather
than cross-imported -- this folder may run in a different context later
(e.g. an Airflow task container) that shouldn't need to import from
streamlit_app.
"""

from __future__ import annotations

import os

import snowflake.connector
from dotenv import load_dotenv

# Loads ml/.env if present. Safe to call even if the file doesn't exist --
# load_dotenv() just no-ops in that case, falling back to whatever's already
# set in the shell environment.
load_dotenv()


def get_connection() -> snowflake.connector.SnowflakeConnection:
    """
    Reads credentials from environment variables, NOT a secrets.toml file --
    this module is meant to run outside Streamlit (plain scripts, later an
    Airflow task), so it can't rely on st.secrets.

    Set these before running anything in ml/:
        SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
        SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE
    """
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "TRAVEL_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "TRAVEL_PLATFORM"),
        schema="ML",
    )