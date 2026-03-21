# 🚀 Flight Data Platform - Run Guide

This guide explains how to start the "Real-Time Flight Data Streaming & Analytics Platform" from scratch.

## Prerequisites
1.  **Docker Desktop** (Running)
2.  **Python 3.10+** (Virtual Environment recommended)
3.  **Snowflake Account** (With Database & Schema created)
4.  **OpenSky Network Account** (Optional, but recommended for higher rate limits)

## Step-by-Step Startup

### 1. Start Infrastructure (Docker)
Start Kafka, Zookeeper, and Redis.
```powershell
docker-compose up -d
```
*Verify:* `docker ps` should show 3 healthy containers.

### 2. Activate Python Environment
```powershell
.\venv\Scripts\activate
```

### 3. Start Data Ingestion (Producer)
This script fetches data from OpenSky and pushes it to Kafka.
```powershell
python ingestion/producer.py
```
*Output:* You should see `✈️ Sent X flights...` logs. Leave this running in a terminal.

### 4. Start Stream Processing (Faust Worker)
This worker consumes from Kafka and writes raw JSON to S3 (Bronze).
```powershell
# Open a NEW terminal
.\venv\Scripts\activate

$env:PYTHONPATH="."
python -m streaming.worker worker -l info
```
*Output:* You should see `Worker: Starting...` and logs about keys being processed.

### 5. Run Orchestration (Dagster)
This pipeline reads from S3, transforms to Parquet (Silver), and loads to Snowflake (Gold).
```powershell
# Open a NEW terminal
.\venv\Scripts\activate

$env:PYTHONPATH="."
dagster dev
```
*Action:* Open http://localhost:3000, go to "Assets", click "Materialize All".

### 6. View Visualization (Streamlit)
Launch the dashboard to see live data.
```powershell
# Open a NEW terminal
.\venv\Scripts\activate

streamlit run dashboard/app.py
```
*Action:* Open http://localhost:8501 in your browser.

## Troubleshooting
*   **Snowflake Error?** Check `.env` credentials and ensure `secrets/rsa_key.p8` is valid.
*   **Kafka Error?** Ensure Docker containers are running (`docker-compose restart`).
*   **No Data?** Ensure the `producer.py` is actually running and fetching flights.
