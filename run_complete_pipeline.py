#!/usr/bin/env python3
"""
Complete Flight Data Pipeline Runner
Orchestrates the entire pipeline from Bronze to Gold
"""

import subprocess
import time
import os
import sys
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step_num, description):
    print(f"\n🔸 Step {step_num}: {description}")

def check_environment():
    """Check if environment is properly set up"""
    print_step(1, "Checking Environment")
    
    # Check if .env file exists
    if not Path('.env').exists():
        print("❌ .env file not found. Please run setup_project.py first")
        return False
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("❌ Virtual environment not activated. Please run: venv\\Scripts\\activate")
        return False
    
    print("✅ Environment check passed")
    return True

def start_kafka_services():
    """Start Kafka and Zookeeper services"""
    print_step(2, "Starting Kafka Services")
    
    try:
        # Check if services are already running
        result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
        if 'kafka' in result.stdout and 'zookeeper' in result.stdout:
            print("✅ Kafka services already running")
            return True
        
        # Start services
        print("🚀 Starting Kafka and Zookeeper...")
        subprocess.run(['docker-compose', 'up', '-d'], check=True)
        
        # Wait for services to be ready
        print("⏳ Waiting for services to be ready...")
        time.sleep(10)
        
        print("✅ Kafka services started successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Kafka services: {e}")
        return False

def run_bronze_to_silver():
    """Run bronze to silver transformation"""
    print_step(3, "Running Bronze to Silver Transformation")
    
    try:
        print("🔄 Processing bronze layer data...")
        result = subprocess.run([
            sys.executable, 'Faust/bronze_to_silver.py'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print("✅ Bronze to Silver transformation completed")
            return True
        else:
            print(f"❌ Bronze to Silver transformation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running bronze to silver: {e}")
        return False

def run_silver_to_gold():
    """Run silver to gold transformation"""
    print_step(4, "Running Silver to Gold Transformation")
    
    try:
        print("🔄 Loading data to Snowflake...")
        result = subprocess.run([
            sys.executable, 'Faust/silver_to_gold.py'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print("✅ Silver to Gold transformation completed")
            return True
        else:
            print(f"❌ Silver to Gold transformation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running silver to gold: {e}")
        return False

def run_analytics_dashboard():
    """Run analytics dashboard"""
    print_step(5, "Generating Analytics Dashboard")
    
    try:
        print("📊 Generating analytics insights...")
        result = subprocess.run([
            sys.executable, 'Faust/analytics_dashboard.py'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print("✅ Analytics dashboard generated")
            print(result.stdout)
            return True
        else:
            print(f"❌ Analytics dashboard failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running analytics dashboard: {e}")
        return False

def main():
    """Main pipeline runner"""
    print_header("Flight Data Pipeline - Complete Run")
    
    # Check environment
    if not check_environment():
        return
    
    # Start Kafka services
    if not start_kafka_services():
        return
    
    # Run bronze to silver
    if not run_bronze_to_silver():
        print("⚠️ Bronze to Silver failed, but continuing...")
    
    # Run silver to gold
    if not run_silver_to_gold():
        print("⚠️ Silver to Gold failed, but continuing...")
    
    # Run analytics dashboard
    if not run_analytics_dashboard():
        print("⚠️ Analytics dashboard failed, but continuing...")
    
    print_header("Pipeline Run Complete!")
    print("""
    Next Steps:
    1. Check your Snowflake account for the FLIGHT_ANALYTICS database
    2. Run individual components as needed:
       - python OpenSky/flight-producer.py (for real-time data)
       - python Faust/bronze_to_silver.py (for data transformation)
       - python Faust/silver_to_gold.py (for Snowflake loading)
       - python Faust/analytics_dashboard.py (for analytics)
    3. Set up Tableau/PowerBI connection to Snowflake for visualization
    """)

if __name__ == "__main__":
    main()

