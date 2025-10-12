#!/usr/bin/env python3
"""
🚀 Flight Streaming System Startup Script
Quick launcher for the unified real-time flight streaming pipeline
"""

import os
import sys
import subprocess
from pathlib import Path

def check_virtual_env():
    """Ensure virtual environment is activated"""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("❌ Virtual environment not activated!")
        print("Please run: venv\\Scripts\\activate")
        return False
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not Path('.env').exists():
        print("❌ .env file not found!")
        print("Please copy env_template.txt to .env and fill in your credentials")
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
        'SNOWFLAKE_USER', 'SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_PRIVATE_KEY_PATH'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def start_docker_services():
    """Start Docker services"""
    print("🐳 Starting Docker services...")
    try:
        subprocess.run(['docker-compose', 'up', '-d'], check=True)
        print("✅ Docker services started")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Docker services: {e}")
        return False

def main():
    """Main startup function"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              🛩️ FLIGHT STREAMING SYSTEM STARTUP             ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Check virtual environment
    if not check_virtual_env():
        return
    
    # Check environment file
    if not check_env_file():
        return
    
    # Install dependencies
    if not install_dependencies():
        return
    
    # Start Docker services
    if not start_docker_services():
        return
    
    print("\n🚀 Starting Flight Streaming Orchestrator...")
    print("Press Ctrl+C to stop the system")
    print("="*60)
    
    # Start the orchestrator
    try:
        subprocess.run([sys.executable, 'flight_streaming_orchestrator.py'])
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Flight Streaming System...")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
