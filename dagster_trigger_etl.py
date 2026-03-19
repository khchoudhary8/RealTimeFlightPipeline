#!/usr/bin/env python3
"""
🎯 Dagster ETL Pipeline Trigger

Manually trigger the ETL pipeline (bronze → silver → gold).

This replaces the old run_complete_pipeline.py script.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dagster_ installation():
    """Check if Dagster CLI is available"""
    try:
        subprocess.run(['dagster', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Dagster CLI not found")
        print("   Install: pip install dagster-cli")
        return False

def main():
    """Trigger the ETL pipeline"""
    print("\n" + "="*60)
    print("🎯 TRIGGERING ETL PIPELINE")
    print("="*60)

    # Check if Dagster is installed
    if not check_dagster_installation():
        sys.exit(1)

    # Check if Dagster daemon is running
    print("\n📋 Checking Dagster daemon status...")
    result = subprocess.run(
        ['dagster', 'daemon', 'status'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ Dagster daemon is not running!")
        print("\nStart it with:")
        print("   dagster-daemon run -f dagster_app/defs.py")
        print("\nThen run this script again.")
        sys.exit(1)

    print("✅ Dagster daemon is running")

    # Trigger the ETL job
    print("\n🚀 Triggering etl_pipeline job...")
    result = subprocess.run(
        ['dagster', 'job', 'execute', '-f', 'dagster_app/defs.py', '-j', 'etl_pipeline'],
        capture_output=False,  # Stream output in real-time
        text=True
    )

    if result.returncode == 0:
        print("\n✅ ETL pipeline completed successfully!")
    else:
        print("\n❌ ETL pipeline failed!")
        print("   Check Dagster UI for details: http://localhost:3000")
        sys.exit(1)

    print("\n📊 Check Dagster UI for asset status:")
    print("   http://localhost:3000")
    print("\n📄 View logs in Dagster UI or run:")
    print("   dagster job logs -f dagster_app/defs.py -j etl_pipeline")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
