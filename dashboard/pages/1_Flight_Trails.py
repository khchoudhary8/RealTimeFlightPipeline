import streamlit as st
import pandas as pd
import pydeck as pdk
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from dashboard.db import get_snowflake_connection

st.set_page_config(page_title="Flight Trails", page_icon="🛤️", layout="wide")
st.title("🛤️ Flight Path Tracker")
st.caption("Select an aircraft to trace its journey across Indian airspace")

try:
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        # Get list of aircraft with multiple data points (so we can draw a path)
        cursor.execute("""
            SELECT ICAO24, 
                   MAX(CALLSIGN) as CALLSIGN,
                   MAX(ORIGIN_COUNTRY) as ORIGIN_COUNTRY,
                   COUNT(*) as DATA_POINTS,
                   MIN(TIME_POSITION) as FIRST_SEEN,
                   MAX(TIME_POSITION) as LAST_SEEN
            FROM FLIGHTS_RAW
            WHERE LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
            GROUP BY ICAO24
            HAVING COUNT(*) >= 2
            ORDER BY DATA_POINTS DESC
            LIMIT 200
        """)
        df_aircraft = cursor.fetch_pandas_all()
    finally:
        conn.close()

    if df_aircraft.empty:
        st.warning("⚠️ No flight path data available yet. Need at least 2 data points per aircraft.")
        st.info("Run the pipeline multiple times (or let it run for a while) to collect trajectory data.")
        st.stop()

    # --- Aircraft Selector ---
    st.markdown("### 🔍 Select Aircraft")

    col1, col2 = st.columns([2, 1])
    with col1:
        # Build display labels
        df_aircraft['label'] = df_aircraft.apply(
            lambda r: f"{r['CALLSIGN'] or 'Unknown'} ({r['ICAO24']}) — {r['DATA_POINTS']} points", axis=1
        )
        selected_label = st.selectbox("Choose a flight:", df_aircraft['label'].tolist())
        selected_idx = df_aircraft[df_aircraft['label'] == selected_label].index[0]
        selected_icao = df_aircraft.loc[selected_idx, 'ICAO24']

    with col2:
        st.metric("Data Points", df_aircraft.loc[selected_idx, 'DATA_POINTS'])
        st.metric("Country", df_aircraft.loc[selected_idx, 'ORIGIN_COUNTRY'])

    # --- Load Path Data ---
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT ICAO24, CALLSIGN, TIME_POSITION,
                   LONGITUDE, LATITUDE, BARO_ALTITUDE, VELOCITY
            FROM FLIGHTS_RAW
            WHERE ICAO24 = '{selected_icao}'
            AND LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
            ORDER BY TIME_POSITION
        """)
        df_path = cursor.fetch_pandas_all()
    finally:
        conn.close()

    if df_path.empty:
        st.warning("No path data found for this aircraft.")
        st.stop()

    st.markdown("---")

    # --- Flight Info ---
    info1, info2, info3, info4 = st.columns(4)
    info1.metric("Callsign", df_path['CALLSIGN'].iloc[0] or "Unknown")
    info2.metric("Max Altitude", f"{df_path['BARO_ALTITUDE'].max():,.0f} m")
    info3.metric("Avg Speed", f"{df_path['VELOCITY'].mean():,.0f} m/s")
    info4.metric("Track Points", len(df_path))

    # --- Build arc data for connected path segments ---
    arcs = []
    for i in range(len(df_path) - 1):
        row_from = df_path.iloc[i]
        row_to = df_path.iloc[i + 1]
        arcs.append({
            'source_lng': float(row_from['LONGITUDE']),
            'source_lat': float(row_from['LATITUDE']),
            'target_lng': float(row_to['LONGITUDE']),
            'target_lat': float(row_to['LATITUDE']),
            'altitude': float(row_to['BARO_ALTITUDE'] or 0),
        })

    df_arcs = pd.DataFrame(arcs)

    # Normalize altitude for color gradient
    df_arcs['altitude'] = df_arcs['altitude'].fillna(0)
    max_alt = df_arcs['altitude'].max() if not df_arcs.empty else 1
    max_alt = max(max_alt, 1)  # avoid division by zero

    # Color: low altitude = green, high altitude = red
    df_arcs['r'] = (df_arcs['altitude'] / max_alt * 255).fillna(0).astype(int).clip(0, 255)
    df_arcs['g'] = (255 - df_arcs['altitude'] / max_alt * 200).fillna(0).astype(int).clip(0, 255)
    df_arcs['b'] = 80

    # --- Map ---
    st.subheader("🗺️ Flight Trail")

    center_lat = df_path['LATITUDE'].mean()
    center_lng = df_path['LONGITUDE'].mean()

    # Path layer (connected line)
    path_data = [{
        'path': df_path[['LONGITUDE', 'LATITUDE']].values.tolist(),
        'name': selected_icao
    }]

    path_layer = pdk.Layer(
        "PathLayer",
        data=path_data,
        get_path="path",
        get_color=[0, 180, 255, 200],
        width_min_pixels=3,
        width_max_pixels=8,
    )

    # Scatter layer for each data point
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_path,
        get_position=["LONGITUDE", "LATITUDE"],
        get_radius=3000,
        get_fill_color=[255, 100, 50, 180],
        pickable=True,
    )

    # Start/End markers
    start_end = pd.DataFrame([
        {'LONGITUDE': df_path.iloc[0]['LONGITUDE'], 'LATITUDE': df_path.iloc[0]['LATITUDE'], 
         'color': [0, 255, 0, 255], 'label': 'START'},
        {'LONGITUDE': df_path.iloc[-1]['LONGITUDE'], 'LATITUDE': df_path.iloc[-1]['LATITUDE'], 
         'color': [255, 0, 0, 255], 'label': 'END'},
    ])

    marker_layer = pdk.Layer(
        "ScatterplotLayer",
        data=start_end,
        get_position=["LONGITUDE", "LATITUDE"],
        get_radius=6000,
        get_fill_color="color",
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lng,
        zoom=5,
        pitch=30,
    )

    deck = pdk.Deck(
        layers=[path_layer, scatter_layer, marker_layer],
        initial_view_state=view_state,
        tooltip={"text": "Callsign: {CALLSIGN}\nAltitude: {BARO_ALTITUDE}m\nVelocity: {VELOCITY} m/s"},
        map_style="mapbox://styles/mapbox/dark-v11",
    )

    st.pydeck_chart(deck)

    st.caption("🟢 Green = Start  |  🔴 Red = End  |  🔵 Blue line = Flight path  |  🟠 Orange dots = Data points")

    # --- Altitude profile over time ---
    st.subheader("📈 Altitude Profile")
    if 'TIME_POSITION' in df_path.columns:
        alt_chart = df_path[['TIME_POSITION', 'BARO_ALTITUDE']].dropna()
        if not alt_chart.empty:
            alt_chart = alt_chart.set_index('TIME_POSITION')
            st.line_chart(alt_chart)

    # --- Speed profile ---
    st.subheader("⚡ Velocity Profile")
    if 'TIME_POSITION' in df_path.columns:
        vel_chart = df_path[['TIME_POSITION', 'VELOCITY']].dropna()
        if not vel_chart.empty:
            vel_chart = vel_chart.set_index('TIME_POSITION')
            st.line_chart(vel_chart)

    # --- Raw Path Data ---
    with st.expander("🔍 Raw Path Data"):
        st.dataframe(df_path)

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Ensure FLIGHTS_RAW table exists and has data.")
