@echo off
REM ============================================================
REM  Flight Data Platform - Stop All Services
REM ============================================================

echo.
echo Stopping all Flight Data Platform services...
echo.

REM Stop Docker containers
echo [1/2] Stopping Docker services...
docker-compose down
echo [OK] Docker services stopped.

REM Kill Python processes (Producer, Consumer, Dagster, Streamlit)
echo [2/2] Stopping Python services...
taskkill /FI "WINDOWTITLE eq Flight Producer" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Flight Consumer" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Dagster" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Streamlit Dashboard" /F >nul 2>&1

echo.
echo All services stopped.
pause
