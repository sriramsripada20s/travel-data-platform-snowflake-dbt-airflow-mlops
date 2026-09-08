from __future__ import annotations

import snowflake.connector
import streamlit as st


@st.cache_resource
def get_connection() -> snowflake.connector.SnowflakeConnection:
    cfg = st.secrets["snowflake"]
    return snowflake.connector.connect(
        account=cfg["account"],
        user=cfg["user"],
        password=cfg["password"],
        role=cfg["role"],
        warehouse=cfg["warehouse"],
        database=cfg["database"],
        schema=cfg["schema"],
    )