import streamlit as st
import pandas as pd
import pydeck as pdk
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from dashboard.db import get_snowflake_connection

st.set_page_config(page_title="Airspace Heatmap", page_icon="🔥", layout="wide")
st.title("🔥 Indian Airspace Heatmap")
st.caption("Density visualization of flight positions — see the busiest air corridors")

try:
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT LATITUDE, LONGITUDE, BARO_ALTITUDE, VELOCITY
            FROM FLIGHTS_RAW
            WHERE LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
        """)
        df = cursor.fetch_pandas_all()
    finally:
        conn.close()

    if df.empty:
        st.warning("⚠️ No flight data available for heatmap.")
        st.stop()

    st.markdown(f"**{len(df):,} data points loaded**")

    # --- Controls ---
    st.markdown("### 🎛️ Heatmap Controls")
    col1, col2, col3 = st.columns(3)

    with col1:
        radius = st.slider("Heatmap Radius", 5000, 50000, 20000, step=5000)
    with col2:
        intensity = st.slider("Intensity", 1, 10, 3)
    with col3:
        elevation_scale = st.slider("3D Elevation Scale", 0, 500, 100, step=50)

    st.markdown("---")

    # --- Standard Heatmap ---
    st.subheader("🌡️ Flight Density Heatmap")

    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        get_position=["LONGITUDE", "LATITUDE"],
        get_weight="VELOCITY",
        radiusPixels=radius // 500,
        intensity=intensity,
        threshold=0.1,
        color_range=[
            [0, 25, 0, 25],
            [0, 85, 0, 100],
            [0, 200, 0, 160],
            [255, 255, 0, 200],
            [255, 165, 0, 220],
            [255, 0, 0, 255],
        ],
    )

    view_state = pdk.ViewState(
        latitude=22.5,  # Center of India
        longitude=78.9,
        zoom=4.5,
        pitch=0,
    )

    deck = pdk.Deck(
        layers=[heatmap_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v11",
    )

    st.pydeck_chart(deck)

    st.markdown("---")

    # --- 3D Hexbin View ---
    st.subheader("🏗️ 3D Hexagon Traffic Volume")
    st.caption("Height = number of flights passing through each hex cell")

    hex_layer = pdk.Layer(
        "HexagonLayer",
        data=df,
        get_position=["LONGITUDE", "LATITUDE"],
        radius=radius,
        elevation_scale=elevation_scale,
        elevation_range=[0, 3000],
        extruded=True,
        pickable=True,
        auto_highlight=True,
        coverage=0.8,
        color_range=[
            [1, 152, 189],
            [73, 227, 206],
            [216, 254, 181],
            [254, 237, 177],
            [254, 173, 84],
            [209, 55, 78],
        ],
    )

    view_state_3d = pdk.ViewState(
        latitude=22.5,
        longitude=78.9,
        zoom=4.5,
        pitch=50,
        bearing=-20,
    )

    deck_3d = pdk.Deck(
        layers=[hex_layer],
        initial_view_state=view_state_3d,
        tooltip={"text": "Flights in hex: {elevationValue}"},
        map_style="mapbox://styles/mapbox/dark-v11",
    )

    st.pydeck_chart(deck_3d)

    # --- Stats ---
    st.markdown("---")
    st.subheader("📊 Airspace Statistics")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Positions", f"{len(df):,}")
    col2.metric("Lat Range", f"{df['LATITUDE'].min():.1f}° to {df['LATITUDE'].max():.1f}°")
    col3.metric("Lon Range", f"{df['LONGITUDE'].min():.1f}° to {df['LONGITUDE'].max():.1f}°")
    col4.metric("Avg Altitude", f"{df['BARO_ALTITUDE'].mean():,.0f} m")

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Ensure FLIGHTS_RAW table exists and has data.")
