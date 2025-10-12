#!/usr/bin/env python3
"""
Quick status check for the Flight Streaming System
"""

import subprocess
import os


def check_docker():
    """Check if Docker services are running"""
    try:
        result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True)
        kafka_running = "kafka" in result.stdout and "Up" in result.stdout
        zookeeper_running = "zookeeper" in result.stdout and "Up" in result.stdout
        return kafka_running and zookeeper_running
    except Exception:
        return False


def check_processes():
    """Check if pipeline processes are running"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe"], capture_output=True, text=True, shell=True
        )
        # Look for our specific processes
        return "python.exe" in result.stdout
    except Exception:
        return False


def check_data():
    """Check if data is being generated"""
    try:
        import boto3
        from dotenv import load_dotenv

        load_dotenv()

        s3 = boto3.client(
            "s3",
            region_name="ap-south-1",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        bucket_name = os.getenv("S3_BUCKET_NAME", "realtimeflightstreamingbucket")

        # Check for recent data
        bronze_response = s3.list_objects_v2(Bucket=bucket_name, Prefix="raw_flights/", MaxKeys=5)

        return bronze_response.get("KeyCount", 0) > 0
    except Exception:
        return False


def main():
    """Quick status check"""
    print("=" * 60)
    print("FLIGHT STREAMING SYSTEM - QUICK STATUS CHECK")
    print("=" * 60)

    # Check Docker
    docker_ok = check_docker()
    print(f"Docker Services: {'[OK]' if docker_ok else '[ERROR]'}")

    # Check Processes
    processes_ok = check_processes()
    print(f"Python Processes: {'[OK]' if processes_ok else '[ERROR]'}")

    # Check Data
    data_ok = check_data()
    print(f"Data Generation: {'[OK]' if data_ok else '[NO DATA YET]'}")

    # Overall status
    if docker_ok and processes_ok:
        print("\n[SUCCESS] System is running!")
        print("Use interactive commands in the main system:")
        print("  - status: Show detailed status")
        print("  - etl: Run manual ETL")
        print("  - dashboard: Show analytics")
        print("  - logs: Show recent logs")
    else:
        print("\n[WARNING] Some components may not be running properly")
        print("Check the main system logs for details")

    print("=" * 60)


if __name__ == "__main__":
    main()
