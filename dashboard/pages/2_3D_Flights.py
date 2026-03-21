import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from dashboard.db import get_snowflake_connection

st.set_page_config(page_title="3D Flights", page_icon="🌐", layout="wide")
st.title("🌐 3D Flight Visualization")
st.caption("Explore flight paths in 3D space — Latitude × Longitude × Altitude")

try:
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ICAO24, CALLSIGN, ORIGIN_COUNTRY,
                   LONGITUDE, LATITUDE, BARO_ALTITUDE, VELOCITY,
                   TIME_POSITION
            FROM FLIGHTS_RAW
            WHERE LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
              AND BARO_ALTITUDE IS NOT NULL AND BARO_ALTITUDE > 0
            ORDER BY TIME_POSITION
            LIMIT 50000
        """)
        df = cursor.fetch_pandas_all()
    finally:
        conn.close()

    if df.empty:
        st.warning("⚠️ No flight data available for 3D visualization.")
        st.stop()

    # --- Filters ---
    st.markdown("### 🎛️ Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        countries = ['All'] + sorted(df['ORIGIN_COUNTRY'].dropna().unique().tolist())
        selected_country = st.selectbox("Country", countries)

    with col2:
        min_alt = st.slider("Minimum Altitude (m)", 0, 15000, 0, step=500)

    with col3:
        max_points = st.slider("Max Data Points", 1000, 50000, 10000, step=1000)

    # Apply filters
    df_filtered = df.copy()
    if selected_country != 'All':
        df_filtered = df_filtered[df_filtered['ORIGIN_COUNTRY'] == selected_country]
    df_filtered = df_filtered[df_filtered['BARO_ALTITUDE'] >= min_alt]
    df_filtered = df_filtered.head(max_points)

    if df_filtered.empty:
        st.warning("No data matches your filters.")
        st.stop()

    st.markdown(f"**Showing {len(df_filtered):,} data points**")
    st.markdown("---")

    # --- 3D Scatter Plot ---
    st.subheader("🏔️ 3D Flight Space")

    fig_3d = px.scatter_3d(
        df_filtered,
        x='LONGITUDE',
        y='LATITUDE',
        z='BARO_ALTITUDE',
        color='ORIGIN_COUNTRY',
        hover_data=['CALLSIGN', 'VELOCITY', 'ICAO24'],
        opacity=0.6,
        title="Flights in 3D Airspace (Lon × Lat × Altitude)",
        labels={
            'LONGITUDE': 'Longitude',
            'LATITUDE': 'Latitude',
            'BARO_ALTITUDE': 'Altitude (m)',
            'ORIGIN_COUNTRY': 'Country'
        },
    )

    fig_3d.update_layout(
        scene=dict(
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            zaxis_title='Altitude (m)',
            bgcolor='rgb(10, 10, 30)',
        ),
        paper_bgcolor='rgb(10, 10, 30)',
        plot_bgcolor='rgb(10, 10, 30)',
        font=dict(color='white'),
        height=700,
        margin=dict(l=0, r=0, t=40, b=0),
    )

    st.plotly_chart(fig_3d, use_container_width=True)

    # --- Individual Aircraft 3D Path ---
    st.markdown("---")
    st.subheader("✈️ Single Aircraft 3D Path")

    # Get aircraft with enough points
    aircraft_counts = df_filtered.groupby('ICAO24').size().reset_index(name='count')
    aircraft_counts = aircraft_counts[aircraft_counts['count'] >= 2].sort_values('count', ascending=False)

    if aircraft_counts.empty:
        st.info("Need aircraft with at least 2 data points to draw 3D paths.")
    else:
        # Build labels
        callsign_map = df_filtered.groupby('ICAO24')['CALLSIGN'].first().to_dict()
        aircraft_counts['label'] = aircraft_counts.apply(
            lambda r: f"{callsign_map.get(r['ICAO24'], 'Unknown')} ({r['ICAO24']}) — {r['count']} pts", axis=1
        )

        selected_ac = st.selectbox("Select aircraft:", aircraft_counts['label'].tolist())
        selected_icao = aircraft_counts[aircraft_counts['label'] == selected_ac]['ICAO24'].iloc[0]

        df_ac = df_filtered[df_filtered['ICAO24'] == selected_icao].sort_values('TIME_POSITION')

        fig_path = go.Figure()

        # 3D line path
        fig_path.add_trace(go.Scatter3d(
            x=df_ac['LONGITUDE'],
            y=df_ac['LATITUDE'],
            z=df_ac['BARO_ALTITUDE'],
            mode='lines+markers',
            marker=dict(
                size=4,
                color=df_ac['BARO_ALTITUDE'],
                colorscale='Turbo',
                colorbar=dict(title='Altitude (m)'),
            ),
            line=dict(color='cyan', width=3),
            text=df_ac.apply(lambda r: f"Alt: {r['BARO_ALTITUDE']:.0f}m | Speed: {r['VELOCITY']:.0f} m/s", axis=1),
            hoverinfo='text',
            name=callsign_map.get(selected_icao, selected_icao)
        ))

        # Start marker
        fig_path.add_trace(go.Scatter3d(
            x=[df_ac.iloc[0]['LONGITUDE']],
            y=[df_ac.iloc[0]['LATITUDE']],
            z=[df_ac.iloc[0]['BARO_ALTITUDE']],
            mode='markers',
            marker=dict(size=10, color='lime', symbol='diamond'),
            name='Start'
        ))

        # End marker
        fig_path.add_trace(go.Scatter3d(
            x=[df_ac.iloc[-1]['LONGITUDE']],
            y=[df_ac.iloc[-1]['LATITUDE']],
            z=[df_ac.iloc[-1]['BARO_ALTITUDE']],
            mode='markers',
            marker=dict(size=10, color='red', symbol='diamond'),
            name='End'
        ))

        fig_path.update_layout(
            scene=dict(
                xaxis_title='Longitude',
                yaxis_title='Latitude',
                zaxis_title='Altitude (m)',
                bgcolor='rgb(10, 10, 30)',
            ),
            paper_bgcolor='rgb(10, 10, 30)',
            plot_bgcolor='rgb(10, 10, 30)',
            font=dict(color='white'),
            height=600,
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=True,
        )

        st.plotly_chart(fig_path, use_container_width=True)

    # --- Altitude vs Velocity Scatter ---
    st.markdown("---")
    st.subheader("📊 Altitude vs Velocity")

    fig_scatter = px.scatter(
        df_filtered,
        x='VELOCITY',
        y='BARO_ALTITUDE',
        color='ORIGIN_COUNTRY',
        opacity=0.5,
        labels={'VELOCITY': 'Velocity (m/s)', 'BARO_ALTITUDE': 'Altitude (m)'},
        hover_data=['CALLSIGN', 'ICAO24'],
    )
    fig_scatter.update_layout(
        paper_bgcolor='rgb(10, 10, 30)',
        plot_bgcolor='rgb(20, 20, 40)',
        font=dict(color='white'),
        height=400,
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Ensure FLIGHTS_RAW table exists and has data.")
