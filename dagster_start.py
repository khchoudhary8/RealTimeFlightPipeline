#!/usr/bin/env python3
"""
🚀 Dagster Flight Pipeline - Startup Script

Replaces the old flight_streaming_orchestrator.py

This script:
1. Checks prerequisites (Docker, environment)
2. Starts Kafka/Zookeeper via docker-compose
3. Starts the flight producer (separate process)
4. Starts Dagster daemon (scheduler)
5. Starts Dagster web UI
6. Monitors all processes
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import signal


def check_prerequisites():
    """Check if all required tools are installed"""
    print("🔍 Checking prerequisites...")

    # Check Python virtual environment
    if not (hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)):
        print("❌ Virtual environment not activated!")
        print("   Run: venv\\Scripts\\activate")
        sys.exit(1)

    # Check .env file
    if not Path(".env").exists():
        print("❌ .env file not found!")
        print("   Copy .env.example to .env and fill in credentials")
        sys.exit(1)

    # Check Docker
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        print("✅ Docker available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker not found or not running")
        print("   Install Docker Desktop and start it")
        sys.exit(1)

    print("✅ Prerequisites check passed")


def start_docker_services():
    """Start Kafka and Zookeeper"""
    print("\n🐳 Starting Docker services (Kafka + Zookeeper)...")
    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        print("✅ Docker services started")

        # Wait for services to be ready
        print("⏳ Waiting for services to be ready...")
        time.sleep(15)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Docker services: {e}")
        return False


def start_flight_producer():
    """Start the flight producer in a separate process"""
    print("\n🛩️  Starting flight producer...")
    try:
        # Start producer in background
        producer_proc = subprocess.Popen(
            [sys.executable, "OpenSky/flight_producer.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        print(f"✅ Flight producer started (PID: {producer_proc.pid})")
        return producer_proc
    except Exception as e:
        print(f"❌ Failed to start flight producer: {e}")
        return None


def check_dagster_installation():
    """Check if Dagster is properly installed"""
    try:
        import dagster

        print(f"✅ Dagster {dagster.__version__} installed")
        return True
    except ImportError:
        print("❌ Dagster not installed")
        print("   Run: pip install dagster dagster-webserver dagster-aws dagster-snowflake")
        return False


def print_dagster_instructions():
    """Print instructions for running Dagster"""
    print("\n" + "=" * 70)
    print("📋 DAGSTER SETUP & USAGE")
    print("=" * 70)
    print("\n1. Start Dagster Daemon (in a new terminal):")
    print("   dagster-daemon run -f dagster_app/defs.py")
    print("\n2. Start Dagster Web UI (in another terminal):")
    print("   dagster dev -f dagster_app/defs.py")
    print("\n3. Or use Dagit (Dagster UI):")
    print("   dagster dev -f dagster_app/defs.py")
    print("\n4. Trigger ETL manually from UI:")
    print("   - Open http://localhost:3000")
    print("   - Click on 'etl_pipeline' job")
    print("   - Click 'Launch Run'")
    print("\n5. Or trigger from CLI:")
    print("   dagster job execute -f dagster_app/defs.py -j etl_pipeline")
    print("\n6. Check schedules:")
    print("   - Schedules run hourly at minute 0")
    print("   - View in UI under 'Schedules' tab")
    print("\n7. View assets:")
    print("   - UI shows all assets and their materialization history")
    print("   - Check 'Asset Catalog' tab")
    print("\n" + "=" * 70)
    print("💡 For production, use:")
    print("   - Dagster daemon as a systemd service")
    print("   - Dagster webserver behind nginx")
    print("   - PostgreSQL for storage (not SQLite)")
    print("=" * 70 + "\n")


def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("🚀 FLIGHT PIPELINE - DAGSTER ORCHESTRATION")
    print("=" * 70)

    # 1. Check prerequisites
    check_prerequisites()

    # 2. Check Dagster installation
    if not check_dagster_installation():
        sys.exit(1)

    # 3. Start Docker services
    if not start_docker_services():
        sys.exit(1)

    # 4. Start flight producer
    producer_proc = start_flight_producer()
    if not producer_proc:
        sys.exit(1)

    # 5. Print instructions
    print_dagster_instructions()

    print("✅ Flight pipeline is running!")
    print("\nComponents running:")
    print(f"   - Flight producer (PID: {producer_proc.pid})")
    print("   - Kafka: localhost:9092")
    print("   - Zookeeper: localhost:2181")
    print("\nTo start Dagster:")
    print("   Terminal 1: dagster-daemon run -f dagster_app/defs.py")
    print("   Terminal 2: dagster dev -f dagster_app/defs.py")
    print("\nPress Ctrl+C to stop everything...")

    try:
        # Keep running and monitor producer
        while True:
            time.sleep(1)
            if producer_proc.poll() is not None:
                print(f"\n⚠️  Flight producer exited with code {producer_proc.returncode}")
                print("   Restarting...")
                producer_proc = start_flight_producer()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        producer_proc.terminate()
        producer_proc.wait()
        print("✅ Clean shutdown complete")


if __name__ == "__main__":
    main()
