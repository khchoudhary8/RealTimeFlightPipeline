import streamlit as st
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings
from db import get_snowflake_connection, get_live_unique_flight_count, get_recent_flights, get_flights_by_date
import datetime

st.set_page_config(
    page_title="Flight Analytics Platform",
    page_icon="✈️",
    layout="wide"
)

# --- Sidebar Branding ---
st.sidebar.markdown("## ✈️ Flight Analytics")
st.sidebar.caption(f"Snowflake: `{settings.SNOWFLAKE_DATABASE}`")
st.sidebar.markdown("---")

# --- Date Filter ---
st.sidebar.subheader("📅 Filter by Date")
today = datetime.date.today()
selected_date = st.sidebar.date_input("Select Date", today)
use_live = selected_date == today

st.sidebar.info("💡 Pro Tip: Select today to see live streaming data. Select a past date to view historical flight captures.")
st.sidebar.markdown("---")

# --- Main Overview Page ---
st.title("✈️ Real-Time Flight Analytics")
st.caption(f"Data Source: OpenSky Network | Warehouse: Snowflake ({settings.SNOWFLAKE_DATABASE})")

try:
    with st.spinner("Fetching latest flight data from Snowflake..."):
        conn = get_snowflake_connection()
        try:
            cursor = conn.cursor()

            # 1. Get Live Unique Aircraft (Last 15m) - Only for today
            live_flights_count = get_live_unique_flight_count() if use_live else 0

            # 2. Get Map Data
            if use_live:
                df_map = get_recent_flights(minutes=15)
            else:
                df_map = get_flights_by_date(selected_date)

            cursor.execute("SELECT * FROM TOP_AIRLINES")
            df_airlines = cursor.fetch_pandas_all()

            cursor.execute("SELECT * FROM DAILY_FLIGHT_COUNTS ORDER BY PARTITION_DATE DESC LIMIT 30")
            df_daily = cursor.fetch_pandas_all()
        finally:
            conn.close()

    if df_map.empty:
        st.warning("⚠️ No flight data in Snowflake yet. Run the Dagster pipeline to populate data.")
        st.info("Once data is loaded, this page will show KPIs, a live map, and business insights.")
        st.stop()

    # --- KPIs ---
    st.markdown("### 📈 Key Performance Indicators")

    active_airlines = df_airlines['AIRLINE_CODE'].nunique() if not df_airlines.empty else 0
    top_country = df_daily.iloc[0]['ORIGIN_COUNTRY'] if not df_daily.empty else "N/A"
    avg_velocity = df_map['VELOCITY'].mean() if not df_map.empty else 0
    avg_altitude = df_map['BARO_ALTITUDE'].mean() if not df_map.empty else 0

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    if use_live:
        kpi1.metric("Live Aircraft (15m)", f"{live_flights_count:,}", help="Unique aircraft seen in the last 15 minutes across all batches.")
    else:
        kpi1.metric("Unique Aircraft (Day)", f"{len(df_map):,}", help="Total unique aircraft captured throughout the entire selected day.")
        
    kpi2.metric("Active Airlines", active_airlines)
    kpi3.metric("Avg Velocity", f"{avg_velocity:.0f} m/s")
    kpi4.metric("Avg Altitude", f"{avg_altitude:.0f} m")
    kpi5.metric("Top Country", top_country)

    st.markdown("---")

    # --- Map & Altitude ---
    col_map, col_alt = st.columns([2, 1])

    with col_map:
        st.subheader("🌍 Live Flight Positions")
        st.map(df_map, latitude="LATITUDE", longitude="LONGITUDE")

    with col_alt:
        st.subheader("✈️ Altitude Distribution")
        alt_bins = df_map['BARO_ALTITUDE'].dropna().value_counts(bins=10).sort_index()
        if not alt_bins.empty:
            alt_bins.index = [f"{int(iv.left)}-{int(iv.right)}m" for iv in alt_bins.index]
            st.bar_chart(alt_bins)

    # --- Business Insights ---
    st.subheader("📊 Business Insights")
    chart1, chart2 = st.columns(2)

    with chart1:
        st.caption("Top Airlines by Flight Volume")
        if not df_airlines.empty:
            st.bar_chart(df_airlines.set_index("AIRLINE_CODE")['FLIGHT_COUNT'])

    with chart2:
        st.caption("Flights by Country")
        if not df_daily.empty:
            df_country = df_daily.groupby('ORIGIN_COUNTRY')['FLIGHT_COUNT'].sum().sort_values(ascending=False).head(10)
            st.bar_chart(df_country)

    # --- Raw Data ---
    with st.expander("🔍 View Raw Flight Data"):
        st.dataframe(df_map.head(100))

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Check Snowflake connection and ensure 'FLIGHTS_RAW' exists.")
