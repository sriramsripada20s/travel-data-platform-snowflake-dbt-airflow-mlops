from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()
session.sql("USE DATABASE TRAVEL_PLATFORM").collect()

st.set_page_config(page_title="Travel Experience Platform", layout="wide")
st.title("Travel experience platform")
st.caption("Sep 2025 – Sep 2026")


def run_query(sql: str) -> pd.DataFrame:
    df = session.sql(sql).to_pandas()
    df.columns = [c.lower() for c in df.columns]
    return df


@st.cache_data(ttl=600)
def get_filter_options() -> tuple[list[str], list[str]]:
    cities = run_query("SELECT DISTINCT city FROM MARTS.DIM_EXPERIENCE ORDER BY city")["city"].tolist()
    categories = run_query("SELECT DISTINCT category FROM MARTS.DIM_EXPERIENCE ORDER BY category")["category"].tolist()
    return ["All"] + cities, ["All"] + categories


def _city_filter(city: str) -> str:
    return "1=1" if city == "All" else f"de.city = '{city}'"


def _category_filter(category: str, alias: str = "de") -> str:
    return "1=1" if category == "All" else f"{alias}.category = '{category}'"


@st.cache_data(ttl=600)
def get_kpis(city: str, category: str) -> pd.DataFrame:
    sql = f"""
        with filtered_bookings as (
            select fb.*
            from MARTS.FACT_BOOKINGS fb
            join MARTS.DIM_EXPERIENCE de on fb.experience_id = de.experience_id
            where {_city_filter(city)} and {_category_filter(category)}
        )
        select
            count(*) as total_bookings,
            sum(case when booking_status = 'CONFIRMED' then booking_amount else 0 end) as gmv,
            sum(case when booking_status in ('CANCELLED', 'REFUNDED') then 1 else 0 end)
                / nullif(count(*), 0) as cancellation_rate
        from filtered_bookings
    """
    return run_query(sql)


@st.cache_data(ttl=600)
def get_repeat_customer_rate() -> float:
    sql = """
        select avg(case when is_repeat_booker then 1.0 else 0.0 end) as repeat_rate
        from INTERMEDIATE.INT_CUSTOMER_ACTIVITY
        where total_bookings > 0
    """
    df = run_query(sql)
    return float(df["repeat_rate"].iloc[0]) if not df.empty else 0.0


@st.cache_data(ttl=600)
def get_monthly_trend(city: str, category: str) -> pd.DataFrame:
    sql = f"""
        select
            dd.year, dd.month, dd.month_name,
            count(*) as bookings,
            sum(case when fb.booking_status = 'CONFIRMED' then fb.booking_amount else 0 end) as revenue
        from MARTS.FACT_BOOKINGS fb
        join MARTS.DIM_DATE dd on fb.date_day = dd.date_day
        join MARTS.DIM_EXPERIENCE de on fb.experience_id = de.experience_id
        where {_city_filter(city)} and {_category_filter(category)}
        group by dd.year, dd.month, dd.month_name
        order by dd.year, dd.month
    """
    return run_query(sql)


@st.cache_data(ttl=600)
def get_revenue_by_city(category: str) -> pd.DataFrame:
    sql = f"""
        select
            de.city,
            sum(case when fb.booking_status = 'CONFIRMED' then fb.booking_amount else 0 end) as revenue
        from MARTS.FACT_BOOKINGS fb
        join MARTS.DIM_EXPERIENCE de on fb.experience_id = de.experience_id
        where {_category_filter(category)}
        group by de.city
        order by revenue desc
    """
    return run_query(sql)


@st.cache_data(ttl=600)
def get_funnel() -> pd.DataFrame:
    sql = """
        select event_type, count(distinct session_id) as sessions
        from MARTS.FACT_WEB_EVENTS
        group by event_type
    """
    order = ["SEARCH", "VIEW_EXPERIENCE", "CHECK_AVAILABILITY", "ADD_TO_CART", "CHECKOUT", "PURCHASE"]
    df = run_query(sql)
    df["event_type"] = pd.Categorical(df["event_type"], categories=order, ordered=True)
    return df.sort_values("event_type")


@st.cache_data(ttl=600)
def get_top_experiences(city: str, category: str, limit: int = 10) -> pd.DataFrame:
    city_clause = "1=1" if city == "All" else f"city = '{city}'"
    category_clause = "1=1" if category == "All" else f"category = '{category}'"

    sql = f"""
        select
            experience_name, city, category,
            sum(total_bookings) as bookings,
            sum(total_capacity - available_capacity) / nullif(sum(total_capacity), 0) as avg_utilization,
            sum(confirmed_booking_amount) as revenue
        from INTERMEDIATE.INT_EXPERIENCE_DAILY_METRICS
        where {city_clause} and {category_clause}
        group by experience_name, city, category
        order by bookings desc
        limit {limit}
    """
    return run_query(sql)

@st.cache_data(ttl=600)
def get_cancellation_by_lead_time(city: str, category: str) -> pd.DataFrame:
    sql = f"""
        select
            case
                when lead_time_days < 3 then '<3d'
                when lead_time_days < 14 then '3-14d'
                when lead_time_days < 60 then '14-60d'
                else '>60d'
            end as lead_time_bucket,
            count(*) as total_bookings,
            sum(case when booking_status in ('CANCELLED', 'REFUNDED') then 1 else 0 end)
                / count(*) as cancellation_rate
        from MARTS.FACT_BOOKINGS fb
        join MARTS.DIM_EXPERIENCE de on fb.experience_id = de.experience_id
        where {_city_filter(city)} and {_category_filter(category)}
        group by lead_time_bucket
    """
    df = run_query(sql)
    order = ["<3d", "3-14d", "14-60d", ">60d"]
    df["lead_time_bucket"] = pd.Categorical(df["lead_time_bucket"], categories=order, ordered=True)
    return df.sort_values("lead_time_bucket")


@st.cache_data(ttl=600)
def get_booking_channel_mix(city: str, category: str) -> pd.DataFrame:
    sql = f"""
        select
            booking_channel,
            count(*) as bookings,
            sum(case when booking_status = 'CONFIRMED' then booking_amount else 0 end) as revenue
        from MARTS.FACT_BOOKINGS fb
        join MARTS.DIM_EXPERIENCE de on fb.experience_id = de.experience_id
        where {_city_filter(city)} and {_category_filter(category)}
        group by booking_channel
        order by bookings desc
    """
    return run_query(sql)


cities, categories = get_filter_options()

filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 3])
with filter_col1:
    selected_city = st.selectbox("City", cities)
with filter_col2:
    selected_category = st.selectbox("Category", categories)
with filter_col3:
    st.write("")
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()

kpis = get_kpis(selected_city, selected_category)
repeat_rate = get_repeat_customer_rate()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
if not kpis.empty:
    total_bookings = int(kpis["total_bookings"].iloc[0] or 0)
    gmv = float(kpis["gmv"].iloc[0] or 0)
    cancellation_rate = float(kpis["cancellation_rate"].iloc[0] or 0)
else:
    total_bookings, gmv, cancellation_rate = 0, 0.0, 0.0

kpi1.metric("Total bookings", f"{total_bookings:,}")
kpi2.metric("GMV", f"${gmv:,.0f}")
kpi3.metric("Cancellation rate", f"{cancellation_rate * 100:.1f}%")
kpi4.metric("Repeat customer rate", f"{repeat_rate * 100:.1f}%")

st.divider()

chart_col1, chart_col2 = st.columns([1.4, 1])
with chart_col1:
    st.subheader("Bookings over time")
    trend = get_monthly_trend(selected_city, selected_category)
    if not trend.empty:
        trend["period"] = trend["month_name"].str.slice(0, 3) + " " + trend["year"].astype(str)
        fig = px.bar(trend, x="period", y="bookings")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No bookings match the current filters.")

with chart_col2:
    st.subheader("Top cities by revenue")
    by_city = get_revenue_by_city(selected_category)
    if not by_city.empty:
        fig = px.bar(by_city.sort_values("revenue"), x="revenue", y="city", orientation="h")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No revenue data available.")

st.divider()

bottom_col1, bottom_col2 = st.columns([1, 1.4])
with bottom_col1:
    st.subheader("Booking funnel")
    funnel = get_funnel()
    if not funnel.empty:
        fig = go.Figure(go.Funnel(y=funnel["event_type"], x=funnel["sessions"]))
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No funnel data available.")

with bottom_col2:
    st.subheader("Top experiences")
    top_experiences = get_top_experiences(selected_city, selected_category)
    if not top_experiences.empty:
        display_df = top_experiences.copy()
        display_df["avg_utilization"] = (display_df["avg_utilization"].astype(float) * 100).round(1).astype(str) + "%"
        display_df["revenue"] = display_df["revenue"].astype(float).apply(lambda v: f"${v:,.0f}")
        st.dataframe(
            display_df.rename(columns={
                "experience_name": "Experience", "city": "City", "category": "Category",
                "bookings": "Bookings", "avg_utilization": "Utilization", "revenue": "Revenue",
            }),
            hide_index=True, use_container_width=True,
        )
    else:
        st.info("No experiences match the current filters.")

st.divider()

third_col1, third_col2 = st.columns([1, 1])

with third_col1:
    st.subheader("Cancellation rate by lead time")
    cancellation_data = get_cancellation_by_lead_time(selected_city, selected_category)
    if not cancellation_data.empty:
        fig = px.bar(
            cancellation_data, x="lead_time_bucket", y="cancellation_rate",
            labels={"lead_time_bucket": "Lead time", "cancellation_rate": "Cancellation rate"},
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data for the current filters.")

with third_col2:
    st.subheader("Booking channel mix")
    channel_data = get_booking_channel_mix(selected_city, selected_category)
    if not channel_data.empty:
        fig = px.pie(channel_data, names="booking_channel", values="bookings", hole=0.4)
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data for the current filters.")