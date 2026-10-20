"""
Air Quality Dashboard
Interactive dashboard for exploring air quality data across European cities.
"""

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Page config ──

st.set_page_config(
    page_title="Air Quality Monitor",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 Global Air Quality Monitor")
st.caption("Real-time air quality data from OpenAQ — WHO threshold alerts across European cities")


@st.cache_resource
def get_connection():
    """Create a read-only DuckDB connection."""
    return duckdb.connect("data/openaq_pipeline.duckdb", read_only=True)


def run_query(query: str):
    """Execute a SQL query and return a DataFrame."""
    con = get_connection()
    return con.sql(query).df()


# ── Load data ──

df_daily = run_query("SELECT * FROM air_quality.city_daily_avg")
df_alerts = run_query("SELECT * FROM air_quality.who_alerts")
df_trends = run_query("SELECT * FROM air_quality.pollutant_trends")
df_locations = run_query("SELECT * FROM air_quality.stg_locations")

# ── Sidebar filters ──

st.sidebar.header("Filters")

countries = sorted(df_daily["country_code"].dropna().unique())
selected_countries = st.sidebar.multiselect("Country", countries, default=countries)

parameters = sorted(df_daily["parameter"].dropna().unique())
selected_params = st.sidebar.multiselect("Pollutant", parameters, default=["pm25"])

if not df_daily.empty and "measurement_date" in df_daily.columns:
    min_date = df_daily["measurement_date"].min()
    max_date = df_daily["measurement_date"].max()
    date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
else:
    date_range = None

# ── Apply filters ──

filtered = df_daily[(df_daily["country_code"].isin(selected_countries)) & (df_daily["parameter"].isin(selected_params))]

if date_range and len(date_range) == 2:
    import pandas as pd

    filtered = filtered[
        (filtered["measurement_date"] >= pd.Timestamp(date_range[0]))
        & (filtered["measurement_date"] <= pd.Timestamp(date_range[1]))
    ]

# ── KPI Row ──

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Cities Monitored", filtered["city"].nunique())
with col2:
    st.metric("Total Readings", f"{len(filtered):,}")
with col3:
    st.metric("Countries", filtered["country_code"].nunique())
with col4:
    alerts_count = len(
        df_alerts[(df_alerts["who_status"] == "EXCEEDED") & (df_alerts["country_code"].isin(selected_countries))]
    )
    st.metric("WHO Alerts", alerts_count)

# ── Top Polluted Cities ──

st.markdown("---")
st.subheader("Top 10 Most Polluted Cities")

if not filtered.empty:
    top_cities = (
        filtered.groupby(["city", "country_code"])["daily_avg"]
        .mean()
        .reset_index()
        .sort_values("daily_avg", ascending=False)
        .head(10)
    )
    top_cities["label"] = top_cities["city"] + " (" + top_cities["country_code"] + ")"

    fig_bar = px.bar(
        top_cities,
        x="daily_avg",
        y="label",
        orientation="h",
        color="daily_avg",
        color_continuous_scale="Reds",
        labels={"daily_avg": "Avg Value", "label": ""},
    )
    fig_bar.update_layout(
        yaxis={"categoryorder": "total ascending"},
        showlegend=False,
        height=400,
    )
    st.plotly_chart(fig_bar, width="stretch")
else:
    st.info("No data for selected filters.")

# ── Pollutant Trends ──

st.markdown("---")
st.subheader("Pollutant Trends Over Time")

filtered_trends = df_trends[
    (df_trends["country_code"].isin(selected_countries)) & (df_trends["parameter"].isin(selected_params))
]

if not filtered_trends.empty:
    available_cities = sorted(filtered_trends["city"].dropna().unique())
    selected_city = st.selectbox("Select city", available_cities)

    city_trends = filtered_trends[filtered_trends["city"] == selected_city]

    if not city_trends.empty:
        fig_line = go.Figure()

        for param in city_trends["parameter"].unique():
            param_data = city_trends[city_trends["parameter"] == param]

            fig_line.add_trace(
                go.Scatter(
                    x=param_data["measurement_date"],
                    y=param_data["daily_avg"],
                    mode="lines+markers",
                    name=f"{param} (daily)",
                    opacity=0.4,
                )
            )

            fig_line.add_trace(
                go.Scatter(
                    x=param_data["measurement_date"],
                    y=param_data["moving_avg_3d"],
                    mode="lines",
                    name=f"{param} (3-day MA)",
                    line={"width": 3},
                )
            )

        fig_line.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            height=450,
            hovermode="x unified",
        )
        st.plotly_chart(fig_line, width="stretch")
    else:
        st.info("No trend data for this city.")
else:
    st.info("No data for selected filters.")

# ── WHO Alerts Table ──

st.markdown("---")
st.subheader("⚠️ WHO Threshold Alerts")

alerts_filtered = df_alerts[
    (df_alerts["who_status"] == "EXCEEDED") & (df_alerts["country_code"].isin(selected_countries))
]

if not alerts_filtered.empty:
    display_alerts = alerts_filtered[
        ["city", "country_code", "parameter", "daily_avg", "units", "measurement_date"]
    ].sort_values("daily_avg", ascending=False)

    display_alerts.columns = ["City", "Country", "Pollutant", "Value", "Units", "Date"]
    st.dataframe(display_alerts, width="stretch", hide_index=True)
else:
    st.success("No WHO threshold exceedances for selected filters.")

# ── Country Comparison ──

st.markdown("---")
st.subheader("🏳️ Country Comparison")

if not filtered.empty:
    country_avg = filtered.groupby(["country_code", "parameter"])["daily_avg"].mean().reset_index()

    fig_compare = px.bar(
        country_avg,
        x="country_code",
        y="daily_avg",
        color="parameter",
        barmode="group",
        labels={"daily_avg": "Avg Value", "country_code": "Country", "parameter": "Pollutant"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_compare.update_layout(height=400)
    st.plotly_chart(fig_compare, width="stretch")
else:
    st.info("No data for selected filters.")


# ── Station Map ──

st.markdown("---")
st.subheader("📍 Monitoring Stations")

map_data = df_locations[
    (df_locations["country_code"].isin(selected_countries))
    & (df_locations["latitude"].notna())
    & (df_locations["longitude"].notna())
]

if not map_data.empty:
    fig_map = px.scatter_map(
        map_data,
        lat="latitude",
        lon="longitude",
        hover_name="location_name",
        hover_data=["city", "country_code"],
        color="country_code",
        zoom=4,
        height=500,
    )
    fig_map.update_layout(map_style="open-street-map")
    st.plotly_chart(fig_map, width="stretch")
else:
    st.info("No station data for selected filters.")

# ── Footer ──

st.markdown("---")
st.caption("Data source: OpenAQ API v3 | WHO Air Quality Guidelines (2021)")
