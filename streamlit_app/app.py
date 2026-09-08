from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from connection import get_connection

from queries import (
    get_filter_options,
    get_funnel,
    get_kpis,
    get_monthly_trend,
    get_repeat_customer_rate,
    get_revenue_by_city,
    get_top_experiences,
)

st.set_page_config(page_title="Travel Experience Platform", layout="wide")

st.title("Travel experience platform")
st.caption("Sep 2025 – Sep 2026")

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
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No experiences match the current filters.")