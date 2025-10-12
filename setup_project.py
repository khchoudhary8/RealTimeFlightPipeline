#!/usr/bin/env python3
"""
Flight Pipeline Project Setup Script
This script helps you set up the project environment and verify configurations.
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step_num, description):
    print(f"\n🔸 Step {step_num}: {description}")

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def check_docker():
    """Check if Docker is running"""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker not found or not running")
        return False

def install_requirements():
    """Install Python requirements"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✅ Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python dependencies")
        return False

def create_env_file():
    """Create .env file from template"""
    env_path = Path('.env')
    template_path = Path('config_template.env')
    
    if env_path.exists():
        print("✅ .env file already exists")
        return True
    
    if template_path.exists():
        # Copy template to .env
        with open(template_path, 'r') as template:
            content = template.read()
        
        with open(env_path, 'w') as env_file:
            env_file.write(content)
        
        print("✅ Created .env file from template")
        print("⚠️  Please edit .env file with your actual AWS credentials")
        return True
    else:
        print("❌ Template file not found")
        return False

def check_kafka_services():
    """Check if Kafka services are running"""
    try:
        result = subprocess.run(['docker-compose', 'ps'], 
                              capture_output=True, text=True, check=True)
        if 'kafka' in result.stdout and 'zookeeper' in result.stdout:
            print("✅ Kafka services are running")
            return True
        else:
            print("⚠️  Kafka services not running. Use: docker-compose up -d")
            return False
    except subprocess.CalledProcessError:
        print("⚠️  Could not check Kafka services. Use: docker-compose up -d")
        return False

def create_directories():
    """Create necessary directories"""
    dirs = ['logs', 'data', 'bronze_flights', 'silver_flights']
    for directory in dirs:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Project directories created")

def main():
    print_header("Flight Pipeline Project Setup")
    
    # Check requirements
    print_step(1, "Checking System Requirements")
    if not check_python_version():
        return
    
    if not check_docker():
        print("Please install Docker and try again")
        return
    
    # Install dependencies
    print_step(2, "Installing Python Dependencies")
    if not install_requirements():
        return
    
    # Create environment file
    print_step(3, "Setting up Environment Configuration")
    create_env_file()
    
    # Create directories
    print_step(4, "Creating Project Directories")
    create_directories()
    
    # Check Kafka
    print_step(5, "Checking Kafka Services")
    check_kafka_services()
    
    print_header("Setup Complete!")
    print("""
Next Steps:
1. Edit .env file with your AWS credentials
2. Start Kafka services: docker-compose up -d
3. Create S3 bucket: realtimeflightstreamingbucket
4. Run the producer: python OpenSky/flight-producer.py
5. Run the consumer: python OpenSky/flight_kafka_consumer_to_s3.py

For detailed instructions, check the README or ask for the next step!
    """)

if __name__ == "__main__":
    main()