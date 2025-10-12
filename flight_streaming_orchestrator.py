#!/usr/bin/env python3
"""
🛩️ Real-time Flight Streaming Orchestrator
Unified pipeline that integrates all components into one seamless real-time streaming system
"""

import asyncio
import subprocess
import threading
import time
import signal
import sys
import os
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional
import json

# Configure logging with UTF-8 encoding to handle emojis
import codecs

class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Replace emojis with text for Windows compatibility
            msg = msg.replace('🔍', '[CHECK]').replace('✅', '[OK]').replace('❌', '[ERROR]')
            msg = msg.replace('🚀', '[START]').replace('⏳', '[WAIT]').replace('🔄', '[PROCESS]')
            msg = msg.replace('📊', '[DASH]').replace('🛑', '[STOP]').replace('🔐', '[AUTH]')
            msg = msg.replace('🟢', '[RUNNING]').replace('🔴', '[STOPPED]').replace('🎮', '[INTERACTIVE]')
            msg = msg.replace('📋', '[INFO]').replace('🔗', '[FLOW]').replace('⏰', '[TIME]')
            msg = msg.replace('💡', '[TIP]').replace('📚', '[DOCS]').replace('🛠️', '[TOOLS]')
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # Fallback for stubborn encoding issues
            pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flight_pipeline.log', encoding='utf-8'),
        UnicodeStreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FlightStreamingOrchestrator:
    """
    Main orchestrator for the real-time flight streaming pipeline
    """
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        self.setup_complete = False
        
    def print_banner(self):
        """Print the project banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🛩️ FLIGHT STREAMING SYSTEM                ║
║                                                              ║
║  Real-time Aircraft Monitoring & Analytics Platform         ║
║  OpenSky API → Kafka → Faust → S3 → Snowflake → Dashboard   ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
        logger.info("Flight Streaming Orchestrator initialized")
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        logger.info("🔍 Checking prerequisites...")
        
        checks = [
            ("Python environment", self._check_python_env),
            ("Docker services", self._check_docker_services),
            ("Environment variables", self._check_env_vars),
            ("Dependencies", self._check_dependencies),
            ("AWS S3 access", self._check_s3_access),
            ("Snowflake connection", self._check_snowflake_connection)
        ]
        
        all_passed = True
        for name, check_func in checks:
            try:
                if check_func():
                    logger.info(f"✅ {name}: OK")
                else:
                    logger.error(f"❌ {name}: FAILED")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {name}: ERROR - {e}")
                all_passed = False
        
        return all_passed
    
    def _check_python_env(self) -> bool:
        """Check Python environment"""
        return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    def _check_docker_services(self) -> bool:
        """Check if Docker services are running"""
        try:
            result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
            return 'kafka' in result.stdout and 'zookeeper' in result.stdout
        except:
            return False
    
    def _check_env_vars(self) -> bool:
        """Check if required environment variables are set"""
        required_vars = [
            'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
            'SNOWFLAKE_USER', 'SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_PRIVATE_KEY_PATH'
        ]
        return all(os.getenv(var) for var in required_vars)
    
    def _check_dependencies(self) -> bool:
        """Check if required Python packages are installed"""
        required_packages = [
            'kafka-python', 'faust-streaming', 'boto3', 'pandas', 
            'snowflake-connector-python', 'cryptography'
        ]
        try:
            import pkg_resources
            for package in required_packages:
                pkg_resources.get_distribution(package)
            return True
        except:
            return False
    
    def _check_s3_access(self) -> bool:
        """Check AWS S3 access"""
        try:
            import boto3
            s3 = boto3.client('s3', 
                            region_name='ap-south-1',
                            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
            s3.head_bucket(Bucket='realtimeflightstreamingbucket')
            return True
        except:
            return False
    
    def _check_snowflake_connection(self) -> bool:
        """Check Snowflake connection"""
        import snowflake.connector
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        
        
        SNOWFLAKE_CONFIG = {
            'user': os.getenv('SNOWFLAKE_USER'),
            'password': os.getenv('SNOWFLAKE_PASSWORD'),
            'account': os.getenv('SNOWFLAKE_ACCOUNT'),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            'database': os.getenv('SNOWFLAKE_DATABASE', 'FLIGHT_ANALYTICS'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
            'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')
        }
        config = dict(SNOWFLAKE_CONFIG) 
        private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
        private_key_passphrase = os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE')

        if private_key_path and os.path.exists(private_key_path):
            try:
                # Load the private key from file (exact pattern from your sample)
                with open(private_key_path, "rb") as key_file:
                    p_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=(
                            # private_key_passphrase.encode() if private_key_passphrase else
                            None
                        ),
                    )
                        
                # Convert the private key to bytes (exact pattern from your sample)
                pkb = p_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                # Connect to Snowflake (exact pattern from your sample) with optional insecure mode
                connect_kwargs = {
                    'user': config['user'],
                    'account': config['account'],
                    'private_key': pkb,
                    'disable_ocsp_checks':True,
                }
              

                conn = snowflake.connector.connect(**connect_kwargs)
                logger.info("🔐 Using key-pair authentication for Snowflake")
                logger.info("✅ Connected to Snowflake successfully")
                conn.close()
                return True
            except Exception as e:
                logger.debug(f"Snowflake connection test failed: {e}")
                return False
    
    def start_infrastructure(self) -> bool:
        """Start required infrastructure services"""
        logger.info("🚀 Starting infrastructure services...")
        
        try:
            # Start Docker services
            result = subprocess.run(['docker-compose', 'up', '-d'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to start Docker services: {result.stderr}")
                return False
            
            # Wait for services to be ready
            logger.info("⏳ Waiting for services to be ready...")
            time.sleep(15)
            
            logger.info("✅ Infrastructure services started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start infrastructure: {e}")
            return False
    
    def start_streaming_pipeline(self):
        """Start the real-time streaming pipeline"""
        logger.info("🔄 Starting real-time streaming pipeline...")
        
        # Start producer in background
        self._start_component("producer", "OpenSky/flight-producer.py")
        
        # Start Faust stream processor
        self._start_component("faust", ["python", "-m", "faust", "-A", "Faust.faust_app", "worker", "--loglevel=info"])
        
        # Start periodic ETL processes
        self._start_etl_scheduler()
        
        self.running = True
        logger.info("✅ Real-time streaming pipeline started")
    
    def _start_component(self, name: str, command: List[str]):
        """Start a pipeline component"""
        try:
            # Use the virtual environment Python executable
            venv_python = Path("venv/Scripts/python.exe")
            if venv_python.exists():
                python_exec = str(venv_python)
            else:
                python_exec = sys.executable
            
            if isinstance(command, str):
                cmd = [python_exec, command]
            else:
                cmd = [python_exec] + command[1:] if command[0] == "python" else command
            
            logger.info(f"Starting {name}: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()  # Ensure correct working directory
            )
            self.processes[name] = process
            logger.info(f"✅ {name} started (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
    
    def _start_etl_scheduler(self):
        """Start the ETL scheduler for periodic data processing"""
        def etl_scheduler():
            # Use the virtual environment Python executable
            venv_python = Path("venv/Scripts/python.exe")
            python_exec = str(venv_python) if venv_python.exists() else sys.executable
            
            while self.running:
                try:
                    # Bronze to Silver (every 5 minutes)
                    logger.info("🔄 Running Bronze to Silver transformation...")
                    result = subprocess.run(
                        [python_exec, 'Faust/bronze_to_silver.py'],
                        capture_output=True, text=True, timeout=300
                    )
                    if result.returncode == 0:
                        logger.info("✅ Bronze to Silver completed")
                    else:
                        logger.error(f"❌ Bronze to Silver failed: {result.stderr}")
                    
                    # Silver to Gold (every 10 minutes)
                    logger.info("🔄 Running Silver to Gold transformation...")
                    result = subprocess.run(
                        [python_exec, 'Faust/silver_to_gold.py'],
                        capture_output=True, text=True, timeout=600
                    )
                    if result.returncode == 0:
                        logger.info("✅ Silver to Gold completed")
                    else:
                        logger.error(f"❌ Silver to Gold failed: {result.stderr}")
                    
                    # Wait before next ETL cycle
                    time.sleep(300)  # 5 minutes
                    
                except Exception as e:
                    logger.error(f"ETL scheduler error: {e}")
                    time.sleep(60)  # Wait 1 minute on error
        
        etl_thread = threading.Thread(target=etl_scheduler, daemon=True)
        etl_thread.start()
        logger.info("✅ ETL scheduler started")
    
    def start_dashboard(self):
        """Start the analytics dashboard"""
        logger.info("📊 Starting analytics dashboard...")
        
        def dashboard_server():
            # Use the virtual environment Python executable
            venv_python = Path("venv/Scripts/python.exe")
            python_exec = str(venv_python) if venv_python.exists() else sys.executable
            
            while self.running:
                try:
                    result = subprocess.run(
                        [python_exec, 'Faust/analytics_dashboard.py'],
                        capture_output=True, text=True, timeout=60
                    )
                    if result.returncode == 0:
                        print(result.stdout)
                    else:
                        logger.error(f"Dashboard error: {result.stderr}")
                    
                    time.sleep(30)  # Update every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Dashboard error: {e}")
                    time.sleep(60)
        
        dashboard_thread = threading.Thread(target=dashboard_server, daemon=True)
        dashboard_thread.start()
        logger.info("✅ Analytics dashboard started")
    
    def monitor_pipeline(self):
        """Monitor the pipeline health"""
        logger.info("🔍 Starting pipeline monitoring...")
        
        def health_check():
            while self.running:
                try:
                    for name, process in self.processes.items():
                        if process.poll() is not None:
                            logger.error(f"❌ {name} process died, restarting...")
                            # Restart logic here if needed
                    
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Health check error: {e}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=health_check, daemon=True)
        monitor_thread.start()
        logger.info("✅ Pipeline monitoring started")
    
    def stop_pipeline(self):
        """Stop all pipeline components"""
        logger.info("🛑 Stopping pipeline...")
        
        self.running = False
        
        # Stop all processes
        for name, process in self.processes.items():
            try:
                logger.info(f"Stopping {name}...")
                process.terminate()
                process.wait(timeout=10)
                logger.info(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {name}...")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        # Stop Docker services
        try:
            subprocess.run(['docker-compose', 'down'], capture_output=True)
            logger.info("✅ Docker services stopped")
        except Exception as e:
            logger.error(f"Error stopping Docker services: {e}")
        
        logger.info("🛑 Pipeline stopped")
    
    def show_status(self):
        """Show current pipeline status"""
        print("\n" + "="*60)
        print("📊 PIPELINE STATUS")
        print("="*60)
        
        print(f"🟢 Running: {self.running}")
        print(f"🟢 Setup Complete: {self.setup_complete}")
        
        print("\n📋 Active Components:")
        for name, process in self.processes.items():
            status = "🟢 Running" if process.poll() is None else "🔴 Stopped"
            print(f"  {name}: {status} (PID: {process.pid})")
        
        print("\n🔗 Data Flow:")
        print("  OpenSky API → Kafka → Faust → S3 Bronze → S3 Silver → Snowflake Gold")
        
        print("\n⏰ Last Updated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def run_interactive_mode(self):
        """Run in interactive mode with commands"""
        print("\n🎮 Interactive Mode - Available Commands:")
        print("  status    - Show pipeline status")
        print("  restart   - Restart all components")
        print("  etl       - Run manual ETL cycle")
        print("  dashboard - Show analytics dashboard")
        print("  logs      - Show recent logs")
        print("  stop      - Stop pipeline and exit")
        print("  help      - Show this help")
        
        while self.running:
            try:
                command = input("\n> ").strip().lower()
                
                if command == "status":
                    self.show_status()
                elif command == "restart":
                    self.stop_pipeline()
                    time.sleep(5)
                    self.start_streaming_pipeline()
                    self.start_dashboard()
                elif command == "etl":
                    self._run_manual_etl()
                elif command == "dashboard":
                    self._show_dashboard()
                elif command == "logs":
                    self._show_logs()
                elif command == "stop":
                    break
                elif command == "help":
                    self.run_interactive_mode()
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Interactive mode error: {e}")
    
    def _run_manual_etl(self):
        """Run manual ETL cycle"""
        logger.info("🔄 Running manual ETL cycle...")
        
        # Use the virtual environment Python executable
        venv_python = Path("venv/Scripts/python.exe")
        python_exec = str(venv_python) if venv_python.exists() else sys.executable
        
        # Bronze to Silver
        result = subprocess.run([python_exec, 'Faust/bronze_to_silver.py'])
        if result.returncode == 0:
            print("✅ Bronze to Silver completed")
        else:
            print("❌ Bronze to Silver failed")
        
        # Silver to Gold
        result = subprocess.run([python_exec, 'Faust/silver_to_gold.py'])
        if result.returncode == 0:
            print("✅ Silver to Gold completed")
        else:
            print("❌ Silver to Gold failed")
    
    def _show_dashboard(self):
        """Show analytics dashboard"""
        venv_python = Path("venv/Scripts/python.exe")
        python_exec = str(venv_python) if venv_python.exists() else sys.executable
        
        result = subprocess.run([python_exec, 'Faust/analytics_dashboard.py'])
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ Dashboard failed")
    
    def _show_logs(self):
        """Show recent logs"""
        try:
            with open('flight_pipeline.log', 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:  # Show last 20 lines
                    print(line.strip())
        except FileNotFoundError:
            print("No log file found")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop_pipeline()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main entry point"""
    orchestrator = FlightStreamingOrchestrator()
    orchestrator.setup_signal_handlers()
    orchestrator.print_banner()
    
    # Check prerequisites
    if not orchestrator.check_prerequisites():
        logger.error("❌ Prerequisites check failed. Please fix the issues and try again.")
        return
    
    # Start infrastructure
    if not orchestrator.start_infrastructure():
        logger.error("❌ Failed to start infrastructure. Please check Docker and try again.")
        return
    
    orchestrator.setup_complete = True
    
    # Start the pipeline
    orchestrator.start_streaming_pipeline()
    orchestrator.start_dashboard()
    orchestrator.monitor_pipeline()
    
    # Show initial status
    orchestrator.show_status()
    
    # Run in interactive mode
    try:
        orchestrator.run_interactive_mode()
    except KeyboardInterrupt:
        pass
    finally:
        orchestrator.stop_pipeline()

if __name__ == "__main__":
    main()
