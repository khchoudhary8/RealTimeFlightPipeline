import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from dashboard.db import get_snowflake_connection

st.set_page_config(page_title="Flight Intelligence", page_icon="🧠", layout="wide")
st.title("🧠 Flight Intelligence")
st.caption("Duration estimation • Anomaly detection • Auto airport detection")

try:
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ICAO24, CALLSIGN, ORIGIN_COUNTRY, TIME_POSITION,
                   LONGITUDE, LATITUDE, BARO_ALTITUDE, VELOCITY
            FROM FLIGHTS_RAW
            WHERE LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
            ORDER BY TIME_POSITION
        """)
        df = cursor.fetch_pandas_all()
    finally:
        conn.close()

    if df.empty:
        st.warning("⚠️ No flight data available for analysis.")
        st.stop()

    st.markdown(f"**Analyzing {len(df):,} data points across {df['ICAO24'].nunique()} aircraft**")

    # ============================================================
    # SECTION 1: FLIGHT DURATION ESTIMATION
    # ============================================================
    st.markdown("---")
    st.subheader("⏱️ Flight Duration in Indian Airspace")
    st.caption("Estimated time each aircraft spent in tracked airspace based on first/last position")

    # Ensure TIME_POSITION is datetime, coercing errors to NaT
    df['TIME_POSITION'] = pd.to_datetime(df['TIME_POSITION'], errors='coerce')
    
    # Drop rows with invalid times
    df = df.dropna(subset=['TIME_POSITION'])

    # Filter out unrealistic years (often caused by 0 timestamps = 1970 or potential corrupt future dates)
    # Keeping only reasonable modern flight data (e.g., post-2000)
    df = df[df['TIME_POSITION'].dt.year > 2000]

    if df.empty:
        st.warning("⚠️ No valid time data available after filtering.")
        st.stop()

    # Group by aircraft
    duration_df = df.groupby('ICAO24').agg(
        callsign=('CALLSIGN', 'first'),
        country=('ORIGIN_COUNTRY', 'first'),
        first_seen=('TIME_POSITION', 'min'),
        last_seen=('TIME_POSITION', 'max'),
        data_points=('ICAO24', 'count'),
        avg_altitude=('BARO_ALTITUDE', 'mean'),
        avg_velocity=('VELOCITY', 'mean'),
    ).reset_index()

    # Calculate duration safely
    # Check if first_seen/last_seen are valid datetimes
    if not pd.api.types.is_datetime64_any_dtype(duration_df['first_seen']):
        duration_df['first_seen'] = pd.to_datetime(duration_df['first_seen'], errors='coerce')
    if not pd.api.types.is_datetime64_any_dtype(duration_df['last_seen']):
        duration_df['last_seen'] = pd.to_datetime(duration_df['last_seen'], errors='coerce')
        
    duration_df = duration_df.dropna(subset=['first_seen', 'last_seen'])

    duration_df['duration_seconds'] = (
        duration_df['last_seen'] - duration_df['first_seen']
    ).dt.total_seconds()

    # Only keep aircraft with reasonable duration (more than 0 seconds)
    duration_df = duration_df[duration_df['duration_seconds'] > 0].copy()
    duration_df['duration_minutes'] = duration_df['duration_seconds'] / 60
    duration_df = duration_df.sort_values('duration_minutes', ascending=False)

    if not duration_df.empty:
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Aircraft", len(duration_df))
        k2.metric("Avg Duration", f"{duration_df['duration_minutes'].mean():.0f} min")
        k3.metric("Longest Flight", f"{duration_df['duration_minutes'].max():.0f} min")
        k4.metric("Shortest Flight", f"{duration_df['duration_minutes'].min():.0f} min")

        # Duration distribution
        fig_dur = px.histogram(
            duration_df, x='duration_minutes', nbins=20,
            labels={'duration_minutes': 'Duration (minutes)'},
            title='Distribution of Flight Durations in Airspace',
            color_discrete_sequence=['#00d4ff'],
        )
        fig_dur.update_layout(
            paper_bgcolor='rgb(10, 10, 30)',
            plot_bgcolor='rgb(20, 20, 40)',
            font=dict(color='white'),
            height=350,
        )
        st.plotly_chart(fig_dur, use_container_width=True)

        # Top 10 longest flights table
        with st.expander("🏆 Top 10 Longest Flights"):
            top10 = duration_df.head(10)[['ICAO24', 'callsign', 'country', 'duration_minutes', 
                                          'data_points', 'avg_altitude', 'avg_velocity']].copy()
            top10.columns = ['ICAO24', 'Callsign', 'Country', 'Duration (min)', 
                            'Data Points', 'Avg Alt (m)', 'Avg Speed (m/s)']
            top10['Duration (min)'] = top10['Duration (min)'].round(1)
            top10['Avg Alt (m)'] = top10['Avg Alt (m)'].round(0)
            top10['Avg Speed (m/s)'] = top10['Avg Speed (m/s)'].round(0)
            st.dataframe(top10, use_container_width=True, hide_index=True)
    else:
        st.info("Need aircraft with multiple data points over time to estimate duration.")

    # ============================================================
    # SECTION 2: ANOMALY DETECTION
    # ============================================================
    st.markdown("---")
    st.subheader("🚨 Flight Anomaly Detection")
    st.caption("Detecting unusual altitude changes and speed variations")

    # Calculate changes per aircraft
    anomalies = []
    for icao, group in df.groupby('ICAO24'):
        if len(group) < 2:
            continue

        group = group.sort_values('TIME_POSITION')
        group = group.copy()

        # Altitude change between consecutive measurements
        group['alt_change'] = group['BARO_ALTITUDE'].diff().abs()
        group['speed_change'] = group['VELOCITY'].diff().abs()
        group['time_diff'] = group['TIME_POSITION'].diff().dt.total_seconds()

        # Flag anomalies:
        # - Altitude drop > 2000m between consecutive readings
        # - Speed change > 100 m/s between consecutive readings
        # - Very low altitude (< 500m) with high speed (possible approach issues)
        alt_anomalies = group[group['alt_change'] > 2000]
        speed_anomalies = group[group['speed_change'] > 100]
        low_alt_fast = group[(group['BARO_ALTITUDE'] < 500) & (group['VELOCITY'] > 150)]

        for _, row in alt_anomalies.iterrows():
            anomalies.append({
                'ICAO24': icao,
                'Callsign': row['CALLSIGN'],
                'Type': '⚠️ Sudden Altitude Change',
                'Detail': f"Δ{row['alt_change']:.0f}m",
                'Altitude': row['BARO_ALTITUDE'],
                'Velocity': row['VELOCITY'],
                'Latitude': row['LATITUDE'],
                'Longitude': row['LONGITUDE'],
                'Time': row['TIME_POSITION'],
            })

        for _, row in speed_anomalies.iterrows():
            anomalies.append({
                'ICAO24': icao,
                'Callsign': row['CALLSIGN'],
                'Type': '⚡ Speed Anomaly',
                'Detail': f"Δ{row['speed_change']:.0f} m/s",
                'Altitude': row['BARO_ALTITUDE'],
                'Velocity': row['VELOCITY'],
                'Latitude': row['LATITUDE'],
                'Longitude': row['LONGITUDE'],
                'Time': row['TIME_POSITION'],
            })

        for _, row in low_alt_fast.iterrows():
            anomalies.append({
                'ICAO24': icao,
                'Callsign': row['CALLSIGN'],
                'Type': '🛬 Low-Alt High-Speed',
                'Detail': f"{row['BARO_ALTITUDE']:.0f}m @ {row['VELOCITY']:.0f}m/s",
                'Altitude': row['BARO_ALTITUDE'],
                'Velocity': row['VELOCITY'],
                'Latitude': row['LATITUDE'],
                'Longitude': row['LONGITUDE'],
                'Time': row['TIME_POSITION'],
            })

    if anomalies:
        df_anomalies = pd.DataFrame(anomalies)

        a1, a2, a3 = st.columns(3)
        a1.metric("Total Anomalies", len(df_anomalies))
        a2.metric("Altitude Anomalies", len(df_anomalies[df_anomalies['Type'].str.contains('Altitude')]))
        a3.metric("Speed Anomalies", len(df_anomalies[df_anomalies['Type'].str.contains('Speed')]))

        # Anomaly breakdown
        fig_anom = px.pie(
            df_anomalies, names='Type', title='Anomaly Types',
            color_discrete_sequence=['#ff6b6b', '#ffd93d', '#6bcb77'],
        )
        fig_anom.update_layout(
            paper_bgcolor='rgb(10, 10, 30)',
            font=dict(color='white'),
            height=350,
        )
        st.plotly_chart(fig_anom, use_container_width=True)

        # Anomaly table
        with st.expander("📋 Anomaly Details"):
            st.dataframe(df_anomalies, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No anomalies detected! All flights operating within normal parameters.")

    # ============================================================
    # SECTION 3: AUTO AIRPORT DETECTION (DBSCAN)
    # ============================================================
    st.markdown("---")
    st.subheader("🛫 Auto Airport Detection (DBSCAN)")
    st.caption("Clustering low-altitude, low-speed positions to detect likely airport locations")

    # Filter for low altitude + low velocity → likely near airports
    df_low = df[(df['BARO_ALTITUDE'] < 1500) & (df['VELOCITY'] < 120)].copy()

    if len(df_low) < 10:
        st.info("Not enough low-altitude data points for airport detection. Need more flight data near airports (altitude < 1500m, speed < 120 m/s).")
    else:
        from sklearn.cluster import DBSCAN

        st.markdown(f"**{len(df_low):,} low-altitude points found for clustering**")

        col1, col2 = st.columns(2)
        with col1:
            eps_km = st.slider("Cluster Radius (km)", 5, 50, 15)
        with col2:
            min_pts = st.slider("Min Points per Cluster", 3, 30, 5)

        # Convert lat/lon to approximate radians for DBSCAN
        coords = df_low[['LATITUDE', 'LONGITUDE']].values
        coords_rad = np.radians(coords)

        # DBSCAN with haversine metric
        db = DBSCAN(
            eps=eps_km / 6371.0,  # Convert km to radians
            min_samples=min_pts,
            metric='haversine',
            algorithm='ball_tree'
        )
        df_low = df_low.copy()
        df_low['cluster'] = db.fit_predict(coords_rad)

        # Filter out noise (-1)
        clustered = df_low[df_low['cluster'] != -1]
        n_clusters = clustered['cluster'].nunique()

        if n_clusters > 0:
            st.success(f"🎯 Detected **{n_clusters}** likely airport/approach zones!")

            # Get cluster centers
            airports = clustered.groupby('cluster').agg(
                lat=('LATITUDE', 'mean'),
                lon=('LONGITUDE', 'mean'),
                avg_alt=('BARO_ALTITUDE', 'mean'),
                avg_vel=('VELOCITY', 'mean'),
                data_points=('ICAO24', 'count'),
                unique_aircraft=('ICAO24', 'nunique'),
            ).reset_index()

            airports = airports.sort_values('data_points', ascending=False)
            airports.columns = ['Cluster', 'Latitude', 'Longitude', 'Avg Altitude (m)', 
                               'Avg Speed (m/s)', 'Data Points', 'Unique Aircraft']

            # Known Indian airports for reference
            known_airports = {
                'DEL (Delhi)': (28.556, 77.100),
                'BOM (Mumbai)': (19.089, 72.868),
                'BLR (Bangalore)': (13.199, 77.706),
                'MAA (Chennai)': (12.990, 80.169),
                'CCU (Kolkata)': (22.654, 88.447),
                'HYD (Hyderabad)': (17.231, 78.430),
                'GOI (Goa)': (15.381, 73.831),
                'COK (Kochi)': (10.152, 76.402),
            }

            # Try to match clusters to known airports
            def match_airport(lat, lon):
                for name, (a_lat, a_lon) in known_airports.items():
                    dist = np.sqrt((lat - a_lat)**2 + (lon - a_lon)**2)
                    if dist < 0.5:  # ~50km threshold
                        return name
                return "Unknown"

            airports['Likely Airport'] = airports.apply(
                lambda r: match_airport(r['Latitude'], r['Longitude']), axis=1
            )

            st.dataframe(airports, use_container_width=True, hide_index=True)

            # Plot detected airports on map
            import pydeck as pdk

            airport_points = airports.copy()
            airport_points.columns = ['Cluster', 'LATITUDE', 'LONGITUDE', 'Avg Alt', 
                                     'Avg Speed', 'Points', 'Aircraft', 'Airport']

            scatter_layer = pdk.Layer(
                "ScatterplotLayer",
                data=airport_points,
                get_position=["LONGITUDE", "LATITUDE"],
                get_radius="Points * 100",
                radius_min_pixels=8,
                radius_max_pixels=40,
                get_fill_color=[255, 50, 50, 200],
                pickable=True,
            )

            text_layer = pdk.Layer(
                "TextLayer",
                data=airport_points,
                get_position=["LONGITUDE", "LATITUDE"],
                get_text="Airport",
                get_size=14,
                get_color=[255, 255, 255, 255],
                get_angle=0,
                get_text_anchor='"middle"',
                get_alignment_baseline='"bottom"',
            )

            view = pdk.ViewState(latitude=22.5, longitude=78.9, zoom=4.5, pitch=0)

            deck = pdk.Deck(
                layers=[scatter_layer, text_layer],
                initial_view_state=view,
                tooltip={"text": "{Airport}\nAircraft: {Aircraft}\nPoints: {Points}"},
                map_style="mapbox://styles/mapbox/dark-v11",
            )

            st.pydeck_chart(deck)
        else:
            st.info("No clusters found with current parameters. Try adjusting the radius or min points.")

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Ensure FLIGHTS_RAW table exists and has data.")
