@echo off
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              🛩️ FLIGHT STREAMING SYSTEM STARTUP             ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found!
    echo Please copy env_template.txt to .env and fill in your credentials
    pause
    exit /b 1
)

REM Start the flight streaming system
echo 🚀 Starting Flight Streaming System...
echo Press Ctrl+C to stop the system
echo.
python start_flight_streaming.py

echo.
echo 🛑 Flight Streaming System stopped.
pause
