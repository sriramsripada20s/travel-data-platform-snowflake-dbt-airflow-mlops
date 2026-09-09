"""
State for the incremental daily generator.
"""

from __future__ import annotations

import datetime as dt

from snowflake_conn import get_connection


def get_last_generated_date() -> dt.date:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT last_generated_date FROM RAW.PIPELINE_STATE")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(
                "PIPELINE_STATE is empty -- run sql/state/01_create_pipeline_state.sql "
                "(including its seed INSERT) before running the incremental generator."
            )
        return row[0]
    finally:
        cur.close()


def advance_last_generated_date(new_date: dt.date) -> None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE RAW.PIPELINE_STATE SET last_generated_date = %(d)s, updated_at = CURRENT_TIMESTAMP()",
            {"d": new_date},
        )
        conn.commit()
    finally:
        cur.close()


def get_next_booking_counter() -> int:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT MAX(TRY_TO_NUMBER(SUBSTR(booking_id, 2))) FROM RAW.RAW_BOOKINGS"
        )
        row = cur.fetchone()
        max_suffix = row[0] if row and row[0] is not None else 90000
        return int(max_suffix) - 90000 + 1
    finally:
        cur.close()


def get_next_event_counter() -> int:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT MAX(TRY_TO_NUMBER(SUBSTR(event_id, 4))) FROM RAW.RAW_WEB_EVENTS"
        )
        row = cur.fetchone()
        max_suffix = row[0] if row and row[0] is not None else 1_000_000
        return int(max_suffix) - 1_000_000 + 1
    finally:
        cur.close()


def get_prior_cancellation_counts() -> dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT customer_id, COUNT(*) AS cancellation_count
            FROM MARTS.FACT_BOOKINGS
            WHERE booking_status IN ('CANCELLED', 'REFUNDED')
              AND customer_id IS NOT NULL
            GROUP BY customer_id
        """)
        return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        cur.close()


def get_existing_customer_ids() -> list[str]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT customer_id FROM MARTS.DIM_CUSTOMER")
        return [row[0] for row in cur.fetchall()]
    finally:
        cur.close()


def get_active_experiences() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT experience_id, experience_name, city, category,
                   capacity, rating, base_price
            FROM MARTS.DIM_EXPERIENCE
            WHERE active_flag = TRUE
        """)
        columns = [c[0].lower() for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
    finally:
        cur.close()