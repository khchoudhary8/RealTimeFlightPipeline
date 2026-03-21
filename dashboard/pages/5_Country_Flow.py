import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from dashboard.db import get_snowflake_connection

st.set_page_config(page_title="Country Flow", page_icon="🌍", layout="wide")
st.title("🌍 Country Flow Analysis")
st.caption("Which countries have the most flights in Indian airspace?")

try:
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ORIGIN_COUNTRY, CALLSIGN, ICAO24, BARO_ALTITUDE, VELOCITY, PARTITION_DATE
            FROM FLIGHTS_RAW
            WHERE ORIGIN_COUNTRY IS NOT NULL
        """)
        df = cursor.fetch_pandas_all()
    finally:
        conn.close()

    if df.empty:
        st.warning("⚠️ No flight data available for country analysis.")
        st.stop()

    # --- Overall Country Distribution ---
    st.markdown("---")
    st.subheader("🏁 Flight Volume by Country")

    country_counts = df.groupby('ORIGIN_COUNTRY').agg(
        total_flights=('ICAO24', 'count'),
        unique_aircraft=('ICAO24', 'nunique'),
        avg_altitude=('BARO_ALTITUDE', 'mean'),
        avg_velocity=('VELOCITY', 'mean'),
    ).reset_index().sort_values('total_flights', ascending=False)

    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Countries", country_counts['ORIGIN_COUNTRY'].nunique())
    k2.metric("Top Country", country_counts.iloc[0]['ORIGIN_COUNTRY'] if not country_counts.empty else "N/A")
    k3.metric("Top Country Flights", f"{country_counts.iloc[0]['total_flights']:,}" if not country_counts.empty else 0)

    # --- Horizontal Bar Chart (Top 15) ---
    top15 = country_counts.head(15)

    fig_bar = px.bar(
        top15,
        y='ORIGIN_COUNTRY',
        x='total_flights',
        orientation='h',
        color='total_flights',
        color_continuous_scale='Viridis',
        title='Top 15 Countries by Flight Volume',
        labels={'total_flights': 'Total Flights', 'ORIGIN_COUNTRY': 'Country'},
    )
    fig_bar.update_layout(
        paper_bgcolor='rgb(10, 10, 30)',
        plot_bgcolor='rgb(20, 20, 40)',
        font=dict(color='white'),
        height=500,
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- Treemap ---
    st.subheader("🗺️ Country Treemap")

    fig_tree = px.treemap(
        country_counts.head(20),
        path=['ORIGIN_COUNTRY'],
        values='total_flights',
        color='avg_altitude',
        color_continuous_scale='RdYlBu_r',
        title='Flight Distribution by Country (size = flights, color = avg altitude)',
    )
    fig_tree.update_layout(
        paper_bgcolor='rgb(10, 10, 30)',
        font=dict(color='white'),
        height=400,
    )
    st.plotly_chart(fig_tree, use_container_width=True)

    # --- Country Performance Comparison ---
    st.markdown("---")
    st.subheader("📊 Country Performance Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("Average Altitude by Country (Top 10)")
        top_alt = country_counts.head(10)
        fig_alt = px.bar(
            top_alt, x='ORIGIN_COUNTRY', y='avg_altitude',
            color='avg_altitude', color_continuous_scale='Turbo',
            labels={'avg_altitude': 'Avg Altitude (m)', 'ORIGIN_COUNTRY': 'Country'},
        )
        fig_alt.update_layout(
            paper_bgcolor='rgb(10, 10, 30)',
            plot_bgcolor='rgb(20, 20, 40)',
            font=dict(color='white'),
            height=350,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_alt, use_container_width=True)

    with col2:
        st.caption("Average Velocity by Country (Top 10)")
        fig_vel = px.bar(
            top_alt, x='ORIGIN_COUNTRY', y='avg_velocity',
            color='avg_velocity', color_continuous_scale='Plasma',
            labels={'avg_velocity': 'Avg Velocity (m/s)', 'ORIGIN_COUNTRY': 'Country'},
        )
        fig_vel.update_layout(
            paper_bgcolor='rgb(10, 10, 30)',
            plot_bgcolor='rgb(20, 20, 40)',
            font=dict(color='white'),
            height=350,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_vel, use_container_width=True)

    # --- Pie Chart ---
    st.subheader("🥧 Market Share")

    # Group smaller countries into "Others"
    top_n = 10
    pie_data = country_counts.head(top_n).copy()
    others = pd.DataFrame([{
        'ORIGIN_COUNTRY': 'Others',
        'total_flights': country_counts.iloc[top_n:]['total_flights'].sum(),
        'unique_aircraft': 0,
        'avg_altitude': 0,
        'avg_velocity': 0,
    }])
    if others.iloc[0]['total_flights'] > 0:
        pie_data = pd.concat([pie_data, others], ignore_index=True)

    fig_pie = px.pie(
        pie_data, values='total_flights', names='ORIGIN_COUNTRY',
        title='Flight Market Share by Country',
        color_discrete_sequence=px.colors.qualitative.Set3,
        hole=0.4,
    )
    fig_pie.update_layout(
        paper_bgcolor='rgb(10, 10, 30)',
        font=dict(color='white'),
        height=400,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # --- Daily Trends by Country (if partition_date exists) ---
    if 'PARTITION_DATE' in df.columns and df['PARTITION_DATE'].notna().any():
        st.markdown("---")
        st.subheader("📈 Daily Trends by Country")

        daily_country = df.groupby(['PARTITION_DATE', 'ORIGIN_COUNTRY']).size().reset_index(name='flights')
        top_countries = country_counts.head(5)['ORIGIN_COUNTRY'].tolist()
        daily_top = daily_country[daily_country['ORIGIN_COUNTRY'].isin(top_countries)]

        if not daily_top.empty:
            fig_trend = px.line(
                daily_top, x='PARTITION_DATE', y='flights', color='ORIGIN_COUNTRY',
                title='Daily Flight Trends (Top 5 Countries)',
                labels={'flights': 'Flights', 'PARTITION_DATE': 'Date'},
            )
            fig_trend.update_layout(
                paper_bgcolor='rgb(10, 10, 30)',
                plot_bgcolor='rgb(20, 20, 40)',
                font=dict(color='white'),
                height=400,
            )
            st.plotly_chart(fig_trend, use_container_width=True)

    # --- Full Data Table ---
    with st.expander("📋 Full Country Statistics"):
        display_df = country_counts.copy()
        display_df.columns = ['Country', 'Total Flights', 'Unique Aircraft', 'Avg Altitude (m)', 'Avg Velocity (m/s)']
        display_df['Avg Altitude (m)'] = display_df['Avg Altitude (m)'].round(0)
        display_df['Avg Velocity (m/s)'] = display_df['Avg Velocity (m/s)'].round(0)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Ensure FLIGHTS_RAW table exists and has data.")
