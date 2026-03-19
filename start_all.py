#!/usr/bin/env python3
"""
🚀 Flight Pipeline - Start All

Starts the entire pipeline with a single command:
1. Docker services (Kafka + Zookeeper)
2. Flight Producer (OpenSky API → Kafka) [with Prometheus metrics]
3. Dagster Daemon (scheduler)
4. Dagster Web UI (monitoring)
5. OPTIONAL: Prometheus + Grafana (with --monitoring flag)

Usage:
    python start_all.py                    # Start without monitoring
    python start_all.py --monitoring       # Start with Prometheus + Grafana

Press Ctrl+C to stop everything gracefully.
"""

import os
import sys
import subprocess
import time
import signal
import threading
import argparse
from pathlib import Path
from datetime import datetime


# Colors for output
class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def log(color, message):
    """Print colored log message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.RESET}")


def check_prerequisites():
    """Check if all required tools are available"""
    log(Colors.BLUE, "🔍 Checking prerequisites...")

    errors = []

    # Check Python venv
    if not (hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)):
        errors.append("Virtual environment not activated. Run: venv\\Scripts\\activate")

    # Check .env file
    if not Path(".env").exists():
        errors.append(".env file not found. Copy .env.example to .env and fill in credentials")

    # Check Docker
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        log(Colors.GREEN, "  ✅ Docker available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("Docker not found or not running. Install Docker Desktop")

    # Check Dagster installation
    try:
        result = subprocess.run(["dagster", "--version"], capture_output=True, text=True)
        log(Colors.GREEN, f"  ✅ Dagster installed: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("Dagster not installed. Run: pip install dagster dagster-webserver dagster-aws dagster-snowflake")

    if errors:
        log(Colors.RED, "❌ Prerequisites failed:")
        for error in errors:
            log(Colors.RED, f"   - {error}")
        return False

    log(Colors.GREEN, "✅ All prerequisites met")
    return True


def start_docker_services():
    """Start Kafka and Zookeeper via Docker Compose"""
    log(Colors.BLUE, "🐳 Starting Docker services (Kafka + Zookeeper)...")

    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True, capture_output=True)
        log(Colors.GREEN, "  ✅ Docker services started")

        # Wait for Kafka to be ready
        log(Colors.YELLOW, "  ⏳ Waiting for Kafka to be ready (15 seconds)...")
        time.sleep(15)

        # Check if Kafka is actually running
        result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True)
        if "kafka" in result.stdout and "Up" in result.stdout:
            log(Colors.GREEN, "  ✅ Kafka is running")
            return True
        else:
            log(Colors.RED, "  ❌ Kafka did not start properly")
            return False
    except subprocess.CalledProcessError as e:
        log(Colors.RED, f"  ❌ Failed to start Docker: {e}")
        return False


def start_flight_producer():
    """Start the flight producer in background"""
    log(Colors.BLUE, "🛩️  Starting flight producer...")

    try:
        # Start producer as subprocess
        producer_proc = subprocess.Popen(
            [sys.executable, "OpenSky/flight_producer.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Give it a moment to start
        time.sleep(3)

        if producer_proc.poll() is not None:
            # Process already exited
            stdout, _ = producer_proc.communicate()
            log(Colors.RED, f"  ❌ Producer exited immediately: {stdout}")
            return None

        log(Colors.GREEN, f"  ✅ Flight producer started (PID: {producer_proc.pid})")
        return producer_proc
    except Exception as e:
        log(Colors.RED, f"  ❌ Failed to start producer: {e}")
        return None


def start_dagster_daemon():
    """Start Dagster daemon in background"""
    log(Colors.BLUE, "📊 Starting Dagster daemon...")

    try:
        daemon_proc = subprocess.Popen(
            ["dagster-daemon", "run", "-f", "dagster_app/defs.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        time.sleep(3)

        if daemon_proc.poll() is not None:
            stdout, _ = daemon_proc.communicate()
            log(Colors.RED, f"  ❌ Daemon exited immediately: {stdout}")
            return None

        log(Colors.GREEN, f"  ✅ Dagster daemon started (PID: {daemon_proc.pid})")
        return daemon_proc
    except Exception as e:
        log(Colors.RED, f"  ❌ Failed to start Dagster daemon: {e}")
        return None


def start_dagster_webserver():
    """Start Dagster web UI in background"""
    log(Colors.BLUE, "🌐 Starting Dagster web UI...")

    try:
        web_proc = subprocess.Popen(
            ["dagster", "dev", "-f", "dagster_app/defs.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        time.sleep(5)

        if web_proc.poll() is not None:
            stdout, _ = web_proc.communicate()
            log(Colors.RED, f"  ❌ Webserver exited immediately: {stdout}")
            return None

        log(Colors.GREEN, f"  ✅ Dagster web UI started (PID: {web_proc.pid})")
        return web_proc
    except Exception as e:
        log(Colors.RED, f"  ❌ Failed to start Dagster webserver: {e}")
        return None


def start_monitoring_stack():
    """Start Prometheus and Grafana via Docker Compose"""
    log(Colors.BLUE, "📈 Starting monitoring stack (Prometheus + Grafana)...")

    try:
        # Start monitoring services
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.monitoring.yml", "up", "-d"], check=True, capture_output=True
        )
        log(Colors.GREEN, "  ✅ Monitoring services started")

        # Wait for services to be ready
        time.sleep(10)

        # Check Prometheus
        try:
            result = subprocess.run(["curl", "-s", "http://localhost:9090/-/healthy"], capture_output=True)
            if result.returncode == 0:
                log(Colors.GREEN, "  ✅ Prometheus is running on http://localhost:9090")
            else:
                log(Colors.YELLOW, "  ⚠️  Prometheus not ready yet")
        except:
            log(Colors.YELLOW, "  ⚠️  Could not check Prometheus health")

        # Check Grafana
        try:
            result = subprocess.run(["curl", "-s", "http://localhost:3001/api/health"], capture_output=True)
            if result.returncode == 0:
                log(Colors.GREEN, "  ✅ Grafana is running on http://localhost:3001")
                log(Colors.YELLOW, "     Login: admin / admin (change password immediately)")
            else:
                log(Colors.YELLOW, "  ⚠️  Grafana not ready yet")
        except:
            log(Colors.YELLOW, "  ⚠️  Could not check Grafana health")

        return True
    except subprocess.CalledProcessError as e:
        log(Colors.RED, f"  ❌ Failed to start monitoring: {e}")
        return False


def monitor_processes(processes):
    """Monitor processes and print their output"""

    def tail_output(proc, name):
        """Continuously read and print process output"""
        for line in iter(proc.stdout.readline, ""):
            if line:
                print(f"[{name}] {line.rstrip()}")

    threads = []
    for name, proc in processes.items():
        if proc:
            thread = threading.Thread(target=tail_output, args=(proc, name), daemon=True)
            thread.start()
            threads.append(thread)


def signal_handler(sig, frame):
    """Handle Ctrl+C and shutdown gracefully"""
    log(Colors.YELLOW, "\n🛑 Shutdown signal received...")

    for name, proc in processes.items():
        if proc:
            log(Colors.YELLOW, f"  Stopping {name} (PID: {proc.pid})...")
            proc.terminate()
            try:
                proc.wait(timeout=10)
                log(Colors.GREEN, f"  ✅ {name} stopped")
            except subprocess.TimeoutExpired:
                log(Colors.RED, f"  ⚠️  {name} didn't stop, killing...")
                proc.kill()

    # Stop monitoring Docker containers if they were started
    if monitoring_enabled:
        log(Colors.YELLOW, "  Stopping monitoring stack...")
        subprocess.run(["docker-compose", "-f", "docker-compose.monitoring.yml", "down"], capture_output=True)

    log(Colors.GREEN, "✅ All processes stopped. Goodbye!")
    sys.exit(0)


def print_startup_summary(processes, monitoring_enabled):
    """Print summary of started components"""
    log(Colors.BOLD, "\n" + "=" * 70)
    log(Colors.BOLD, "✅ FLIGHT PIPELINE STARTED SUCCESSFULLY")
    log(Colors.BOLD, "=" * 70)

    log(Colors.GREEN, "\nComponents running:")
    if processes.get("producer"):
        log(Colors.GREEN, f"  ✅ Flight Producer (PID: {processes['producer'].pid})")
    else:
        log(Colors.RED, "  ❌ Flight Producer - FAILED")

    if processes.get("daemon"):
        log(Colors.GREEN, f"  ✅ Dagster Daemon (PID: {processes['daemon'].pid})")
    else:
        log(Colors.RED, "  ❌ Dagster Daemon - FAILED")

    if processes.get("webserver"):
        log(Colors.GREEN, f"  ✅ Dagster Web UI (PID: {processes['webserver'].pid})")
    else:
        log(Colors.RED, "  ❌ Dagster Web UI - FAILED")

    if monitoring_enabled:
        log(Colors.GREEN, "  ✅ Monitoring Stack (Prometheus + Grafana)")
    else:
        log(Colors.YELLOW, "  ⚠️  Monitoring NOT enabled (use --monitoring flag)")

    log(Colors.BLUE, "\n📊 Access Points:")
    log(Colors.BLUE, "  • Dagster UI: http://localhost:3000")
    if monitoring_enabled:
        log(Colors.BLUE, "  • Prometheus: http://localhost:9090")
        log(Colors.BLUE, "  • Grafana: http://localhost:3001 (admin/admin)")
    log(Colors.BLUE, "  • Kafka: localhost:9092")
    log(Colors.BLUE, "  • Zookeeper: localhost:2181")

    log(Colors.YELLOW, "\n📋 Next Steps:")
    log(Colors.YELLOW, "  1. Open http://localhost:3000 (Dagster UI)")
    log(Colors.YELLOW, "  2. Click 'Jobs' → 'etl_pipeline' → 'Launch Run'")
    log(Colors.YELLOW, "  3. Check metrics at http://localhost:9090 (if monitoring enabled)")
    log(Colors.YELLOW, "  4. View dashboard at http://localhost:3001 (Grafana)")

    log(Colors.YELLOW, "\n⌨️  Press Ctrl+C to stop everything\n")
    log(Colors.BOLD, "=" * 70 + "\n")


def main():
    """Main entry point"""
    global processes, monitoring_enabled
    processes = {}
    monitoring_enabled = False

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start Flight Pipeline")
    parser.add_argument("--monitoring", action="store_true", help="Start Prometheus + Grafana monitoring stack")
    args = parser.parse_args()
    monitoring_enabled = args.monitoring

    log(Colors.BOLD, "\n" + "=" * 70)
    log(Colors.BOLD, "🚀 FLIGHT PIPELINE - START ALL")
    if monitoring_enabled:
        log(Colors.BOLD, "📈 Monitoring Stack: ENABLED")
    log(Colors.BOLD, "=" * 70)

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 1. Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # 2. Start Docker services (Kafka)
    if not start_docker_services():
        sys.exit(1)

    # 3. Start flight producer
    producer_proc = start_flight_producer()
    if not producer_proc:
        sys.exit(1)
    processes["producer"] = producer_proc

    # 4. Start Dagster daemon
    daemon_proc = start_dagster_daemon()
    if not daemon_proc:
        producer_proc.terminate()
        sys.exit(1)
    processes["daemon"] = daemon_proc

    # 5. Start Dagster webserver
    web_proc = start_dagster_webserver()
    if not web_proc:
        producer_proc.terminate()
        daemon_proc.terminate()
        sys.exit(1)
    processes["webserver"] = web_proc

    # 6. Optionally start monitoring stack
    if monitoring_enabled:
        if not start_monitoring_stack():
            log(Colors.YELLOW, "⚠️  Monitoring stack failed to start, continuing without it...")

    # 7. Start monitoring in background
    monitor_thread = threading.Thread(target=monitor_processes, args=(processes,), daemon=True)
    monitor_thread.start()

    # 8. Print summary
    print_startup_summary(processes, monitoring_enabled)

    # 9. Keep main thread alive and monitor for crashes
    try:
        while True:
            time.sleep(1)

            # Check if any process died
            for name, proc in list(processes.items()):
                if proc and proc.poll() is not None:
                    log(Colors.RED, f"\n⚠️  {name} (PID: {proc.pid}) crashed with exit code {proc.returncode}")
                    log(Colors.YELLOW, f"   Reading last output...")
                    try:
                        output, _ = proc.communicate(timeout=5)
                        last_lines = output[-500:] if len(output) > 500 else output
                        log(Colors.YELLOW, f"   Last output: {last_lines}")
                    except:
                        pass

                    if name == "producer":
                        log(Colors.YELLOW, f"   🔄 Restarting {name}...")
                        processes[name] = start_flight_producer()
                    else:
                        log(Colors.RED, f"   ❌ {name} crashed. Please restart manually.")
                        processes[name] = None

            # Exit if all critical processes died
            if not processes.get("producer") and not processes.get("daemon"):
                log(Colors.RED, "❌ All critical processes stopped. Exiting.")
                sys.exit(1)

    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    processes = {}
    main()
