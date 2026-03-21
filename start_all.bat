@echo off
REM ============================================================
REM  Flight Data Platform - One-Click Startup Script
REM  Starts: Docker (Kafka/Redis) → Producer → Consumer → Dagster → Streamlit
REM ============================================================

echo.
echo ====================================================
echo   Flight Data Platform - Starting All Services
echo ====================================================
echo.

REM --- Step 1: Start Docker services (Kafka, Zookeeper, Redis) ---
echo [1/5] Starting Docker services (Kafka, Zookeeper, Redis)...
docker-compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker failed to start. Make sure Docker Desktop is running.
    pause
    exit /b 1
)
echo [OK] Docker services started.

REM Wait for Kafka to be ready
echo       Waiting 10s for Kafka to initialize...
timeout /t 10 /nobreak >nul

REM --- Step 2: Start Producer (API -> Kafka) ---
echo [2/5] Starting Producer (OpenSky API to Kafka)...
start "Flight Producer" cmd /k "cd /d %~dp0 && .\venv\Scripts\activate && python ingestion\producer.py"
echo [OK] Producer started in new window.

REM --- Step 3: Start Consumer/Worker (Kafka -> S3) ---
echo [3/5] Starting Streaming Worker (Kafka to S3)...
start "Flight Consumer" cmd /k "cd /d %~dp0 && .\venv\Scripts\activate && python -m streaming.worker worker -l info"
echo [OK] Streaming worker started in new window.

REM --- Step 4: Start Dagster ---
echo [4/5] Starting Dagster (Orchestration)...
start "Dagster" cmd /k "cd /d %~dp0 && .\venv\Scripts\activate && dagster dev"
echo [OK] Dagster started in new window.

REM Wait for Dagster to initialize
timeout /t 5 /nobreak >nul

REM --- Step 5: Start Streamlit Dashboard ---
echo [5/5] Starting Streamlit Dashboard...
start "Streamlit Dashboard" cmd /k "cd /d %~dp0 && .\venv\Scripts\activate && streamlit run dashboard\app.py"
echo [OK] Streamlit started in new window.

echo.
echo ====================================================
echo   All services started successfully!
echo ====================================================
echo.
echo   Producer:    Polling OpenSky API every 20s
echo   Consumer:    Writing to S3 Bronze
echo   Dagster:     http://localhost:3000
echo   Dashboard:   http://localhost:8501
echo.
echo   To stop all: Close all windows + run stop_all.bat
echo ====================================================
pause
