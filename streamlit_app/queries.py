from __future__ import annotations

import pandas as pd
import streamlit as st

# Custom module to handle Snowflake database connection pooling
from connection import get_connection

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or {})
        columns = [c[0].lower() for c in cur.description]
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=columns)
        # Snowflake returns NUMBER/DECIMAL columns as Python's decimal.Decimal,
        # which doesn't mix with plain floats in arithmetic (e.g. Decimal * 100
        # raises TypeError). Convert every numeric-looking column to float here,
        # once, so no downstream code needs to remember to do it.
        for col in df.columns:
            if df[col].map(lambda x: isinstance(x, __import__("decimal").Decimal)).any():
                df[col] = df[col].astype(float)
        return df
    finally:
        cur.close()


# ============================================================================
# CACHED DATA RETRIEVAL FUNCTIONS (TTL = 10 Minutes)
# ============================================================================

@st.cache_data(ttl=600)
def get_filter_options() -> tuple[list[str], list[str]]:
    """
    Populates dropdown filter selections for City and Category from the Experience dimension.
    Appends an 'All' option to the top of both lists.
    """
    cities = run_query(
        "SELECT DISTINCT city FROM MARTS.DIM_EXPERIENCE ORDER BY city"
    )["city"].tolist()
    categories = run_query(
        "SELECT DISTINCT category FROM MARTS.DIM_EXPERIENCE ORDER BY category"
    )["category"].tolist()
    return ["All"] + cities, ["All"] + categories


@st.cache_data(ttl=600)
def get_kpis(city: str, category: str) -> pd.DataFrame:
    """
    Computes top-level executive KPIs based on user-selected filters:
    1. Total Bookings Count
    2. Gross Merchandise Value (GMV) - Sum of confirmed booking amounts
    3. Cancellation Rate - Percentage of bookings cancelled or refunded
    """
    sql = """
        with filtered_bookings as (
            select fb.*
            from MARTS.FACT_BOOKINGS fb
            join MARTS.DIM_EXPERIENCE de on fb.experience_id = de.experience_id
            where (%(city)s = 'All' or de.city = %(city)s)
              and (%(category)s = 'All' or de.category = %(category)s)
        )
        select
            count(*) as total_bookings,
            sum(case when booking_status = 'CONFIRMED' then booking_amount else 0 end) as gmv,
            sum(case when booking_status in ('CANCELLED', 'REFUNDED') then 1 else 0 end)
                / nullif(count(*), 0) as cancellation_rate
        from filtered_bookings
    """
    return run_query(sql, {"city": city, "category": category})


@st.cache_data(ttl=600)
def get_repeat_customer_rate() -> float:
    """
    Calculates overall platform repeat customer rate.
    Evaluates the average percentage of active customers who made >1 booking.
    """
    sql = """
        select avg(case when is_repeat_booker then 1.0 else 0.0 end) as repeat_rate
        from INTERMEDIATE.INT_CUSTOMER_ACTIVITY
        where total_bookings > 0
    """
    df = run_query(sql)
    return float(df["repeat_rate"].iloc[0]) if not df.empty else 0.0


@st.cache_data(ttl=600)
def get_monthly_trend(city: str, category: str) -> pd.DataFrame:
    """
    Aggregates monthly booking volume and confirmed revenue over time.
    Joins Fact Bookings to Conformed Date and Experience Dimensions.
    """
    sql = """
        select
            dd.year,
            dd.month,
            dd.month_name,
            count(*) as bookings,
            sum(case when fb.booking_status = 'CONFIRMED' then fb.booking_amount else 0 end) as revenue
        from MARTS.FACT_BOOKINGS fb
        join MARTS.DIM_DATE dd on fb.date_day = dd.date_day
        join MARTS.DIM_EXPERIENCE de on fb.experience_id = de.experience_id
        where (%(city)s = 'All' or de.city = %(city)s)
          and (%(category)s = 'All' or de.category = %(category)s)
        group by dd.year, dd.month, dd.month_name
        order by dd.year, dd.month
    """
    return run_query(sql, {"city": city, "category": category})


@st.cache_data(ttl=600)
def get_revenue_by_city(category: str) -> pd.DataFrame:
    """
    Ranks total confirmed revenue by city for regional distribution analysis.
    """
    sql = """
        select
            de.city,
            sum(case when fb.booking_status = 'CONFIRMED' then fb.booking_amount else 0 end) as revenue
        from MARTS.FACT_BOOKINGS fb
        join MARTS.DIM_EXPERIENCE de on fb.experience_id = de.experience_id
        where (%(category)s = 'All' or de.category = %(category)s)
        group by de.city
        order by revenue desc
    """
    return run_query(sql, {"category": category})


@st.cache_data(ttl=600)
def get_funnel() -> pd.DataFrame:
    """
    Calculates distinct user sessions across conversion funnel stages.
    
    NOTE: Unfiltered by city/category because top-of-funnel events (SEARCH) 
    do not have a specific experience_id attached yet.
    """
    sql = """
        select event_type, count(distinct session_id) as sessions
        from MARTS.FACT_WEB_EVENTS
        group by event_type
    """
    # Enforce logical funnel stage sequence
    order = ["SEARCH", "VIEW_EXPERIENCE", "CHECK_AVAILABILITY", "ADD_TO_CART", "CHECKOUT", "PURCHASE"]
    df = run_query(sql)
    df["event_type"] = pd.Categorical(df["event_type"], categories=order, ordered=True)
    return df.sort_values("event_type")


@st.cache_data(ttl=600)
def get_top_experiences(city: str, category: str, limit: int = 10) -> pd.DataFrame:
    """
    Retrieves top-performing experiences ranked by booking volume, 
    along with average capacity utilization rate and confirmed revenue.
    """
    sql = """
        select
            experience_name,
            city,
            category,
            sum(total_bookings) as bookings,
            avg(utilization_rate) as avg_utilization,
            sum(confirmed_booking_amount) as revenue
        from INTERMEDIATE.INT_EXPERIENCE_DAILY_METRICS
        where (%(city)s = 'All' or city = %(city)s)
          and (%(category)s = 'All' or category = %(category)s)
        group by experience_name, city, category
        order by bookings desc
        limit %(limit)s
    """
    return run_query(sql, {"city": city, "category": category, "limit": limit})