"""
Snowflake connection for the incremental generator. Self-contained copy of
the same .env-based pattern used in ml/config.py.
"""

from __future__ import annotations

import os

import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "TRAVEL_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "TRAVEL_PLATFORM"),
        schema="RAW",
    )