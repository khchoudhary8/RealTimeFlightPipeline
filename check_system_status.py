#!/usr/bin/env python3
"""
🔍 Flight Streaming System Status Checker
Comprehensive health check for all system components
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemStatusChecker:
    """Comprehensive system status checker"""
    
    def __init__(self):
        self.status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'components': {}
        }
    
    def check_environment(self):
        """Check Python environment and dependencies"""
        logger.info("🔍 Checking Python environment...")
        
        env_status = {
            'python_version': sys.version,
            'virtual_env': self._check_virtual_env(),
            'dependencies': self._check_dependencies(),
            'env_file': Path('.env').exists()
        }
        
        self.status['components']['environment'] = env_status
        return all([env_status['virtual_env'], env_status['dependencies'], env_status['env_file']])
    
    def _check_virtual_env(self):
        """Check if virtual environment is activated"""
        return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    def _check_dependencies(self):
        """Check if required dependencies are installed"""
        required_packages = [
            'kafka-python', 'faust-streaming', 'boto3', 'pandas', 
            'snowflake-connector-python', 'cryptography', 'python-dotenv'
        ]
        
        try:
            import pkg_resources
            installed = []
            for package in required_packages:
                try:
                    dist = pkg_resources.get_distribution(package)
                    installed.append(f"{package}=={dist.version}")
                except pkg_resources.DistributionNotFound:
                    installed.append(f"{package} (NOT INSTALLED)")
            
            return {
                'installed': installed,
                'all_installed': all('NOT INSTALLED' not in pkg for pkg in installed)
            }
        except Exception as e:
            return {'error': str(e), 'all_installed': False}
    
    def check_docker_services(self):
        """Check Docker services status"""
        logger.info("🐳 Checking Docker services...")
        
        try:
            result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
            
            docker_status = {
                'kafka_running': 'kafka' in result.stdout and 'Up' in result.stdout,
                'zookeeper_running': 'zookeeper' in result.stdout and 'Up' in result.stdout,
                'raw_output': result.stdout
            }
            
            self.status['components']['docker'] = docker_status
            return docker_status['kafka_running'] and docker_status['zookeeper_running']
            
        except Exception as e:
            docker_status = {'error': str(e)}
            self.status['components']['docker'] = docker_status
            return False
    
    def check_aws_connection(self):
        """Check AWS S3 connection"""
        logger.info("☁️ Checking AWS S3 connection...")
        
        try:
            import boto3
            from dotenv import load_dotenv
            load_dotenv()
            
            s3 = boto3.client('s3', 
                            region_name='ap-south-1',
                            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
            
            bucket_name = os.getenv('S3_BUCKET_NAME', 'realtimeflightstreamingbucket')
            s3.head_bucket(Bucket=bucket_name)
            
            # List some objects to verify access
            response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
            
            aws_status = {
                'connected': True,
                'bucket': bucket_name,
                'object_count': response.get('KeyCount', 0),
                'region': 'ap-south-1'
            }
            
            self.status['components']['aws'] = aws_status
            return True
            
        except Exception as e:
            aws_status = {'connected': False, 'error': str(e)}
            self.status['components']['aws'] = aws_status
            return False
    
    def check_snowflake_connection(self):
        """Check Snowflake connection"""
        logger.info("❄️ Checking Snowflake connection...")
        
        try:
            import snowflake.connector
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            from dotenv import load_dotenv
            load_dotenv()
            
            private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
            if not private_key_path or not Path(private_key_path).exists():
                snowflake_status = {
                    'connected': False,
                    'error': 'Private key file not found or not specified'
                }
                self.status['components']['snowflake'] = snowflake_status
                return False
            
            with open(private_key_path, 'rb') as key:
                p_key = serialization.load_pem_private_key(
                    key.read(),
                    password=os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE', '').encode('utf-8') or None,
                    backend=default_backend()
                )
            
            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            conn = snowflake.connector.connect(
                user=os.getenv('SNOWFLAKE_USER'),
                account=os.getenv('SNOWFLAKE_ACCOUNT'),
                private_key=pkb,
                disable_ocsp_checks=True
            )
            
            # Test query
            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_USER(), CURRENT_ACCOUNT(), CURRENT_DATABASE()")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            snowflake_status = {
                'connected': True,
                'user': result[0] if result else 'unknown',
                'account': result[1] if result else 'unknown',
                'database': result[2] if result else 'unknown'
            }
            
            self.status['components']['snowflake'] = snowflake_status
            return True
            
        except Exception as e:
            snowflake_status = {'connected': False, 'error': str(e)}
            self.status['components']['snowflake'] = snowflake_status
            return False
    
    def check_data_availability(self):
        """Check data availability in S3"""
        logger.info("📊 Checking data availability...")
        
        try:
            import boto3
            from dotenv import load_dotenv
            load_dotenv()
            
            s3 = boto3.client('s3', 
                            region_name='ap-south-1',
                            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
            
            bucket_name = os.getenv('S3_BUCKET_NAME', 'realtimeflightstreamingbucket')
            
            # Check bronze layer
            bronze_response = s3.list_objects_v2(
                Bucket=bucket_name, 
                Prefix='raw_flights/',
                MaxKeys=10
            )
            
            # Check silver layer
            silver_response = s3.list_objects_v2(
                Bucket=bucket_name, 
                Prefix='silver_flights/',
                MaxKeys=10
            )
            
            data_status = {
                'bronze_objects': bronze_response.get('KeyCount', 0),
                'silver_objects': silver_response.get('KeyCount', 0),
                'bronze_sample': [obj['Key'] for obj in bronze_response.get('Contents', [])[:3]],
                'silver_sample': [obj['Key'] for obj in silver_response.get('Contents', [])[:3]]
            }
            
            self.status['components']['data'] = data_status
            return True
            
        except Exception as e:
            data_status = {'error': str(e)}
            self.status['components']['data'] = data_status
            return False
    
    def check_configuration(self):
        """Check configuration validity"""
        logger.info("⚙️ Checking configuration...")
        
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            required_vars = [
                'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                'SNOWFLAKE_USER', 'SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_PRIVATE_KEY_PATH'
            ]
            
            config_status = {
                'required_vars': {},
                'all_set': True
            }
            
            for var in required_vars:
                value = os.getenv(var)
                config_status['required_vars'][var] = '✅ Set' if value else '❌ Missing'
                if not value:
                    config_status['all_set'] = False
            
            # Check optional vars
            optional_vars = [
                'KAFKA_BOOTSTRAP_SERVERS', 'S3_BUCKET_NAME', 
                'SNOWFLAKE_DATABASE', 'SNOWFLAKE_SCHEMA'
            ]
            
            config_status['optional_vars'] = {}
            for var in optional_vars:
                value = os.getenv(var)
                config_status['optional_vars'][var] = value or 'Using default'
            
            self.status['components']['configuration'] = config_status
            return config_status['all_set']
            
        except Exception as e:
            config_status = {'error': str(e), 'all_set': False}
            self.status['components']['configuration'] = config_status
            return False
    
    def run_all_checks(self):
        """Run all system checks"""
        logger.info("🚀 Running comprehensive system checks...")
        
        checks = [
            ('Environment', self.check_environment),
            ('Docker Services', self.check_docker_services),
            ('AWS Connection', self.check_aws_connection),
            ('Snowflake Connection', self.check_snowflake_connection),
            ('Data Availability', self.check_data_availability),
            ('Configuration', self.check_configuration)
        ]
        
        results = {}
        for name, check_func in checks:
            try:
                results[name] = check_func()
            except Exception as e:
                logger.error(f"Error checking {name}: {e}")
                results[name] = False
        
        # Determine overall status
        passed_checks = sum(results.values())
        total_checks = len(results)
        
        if passed_checks == total_checks:
            self.status['overall_status'] = 'healthy'
        elif passed_checks >= total_checks * 0.7:  # 70% pass rate
            self.status['overall_status'] = 'warning'
        else:
            self.status['overall_status'] = 'critical'
        
        self.status['check_results'] = results
        self.status['passed_checks'] = passed_checks
        self.status['total_checks'] = total_checks
        
        return self.status
    
    def print_status_report(self):
        """Print a formatted status report"""
        print("\n" + "="*80)
        print("🔍 FLIGHT STREAMING SYSTEM STATUS REPORT")
        print("="*80)
        print(f"📅 Timestamp: {self.status['timestamp']}")
        print(f"🎯 Overall Status: {self.status['overall_status'].upper()}")
        print(f"📊 Checks Passed: {self.status['passed_checks']}/{self.status['total_checks']}")
        print("="*80)
        
        # Component status
        for component, details in self.status['components'].items():
            print(f"\n🔧 {component.upper()}")
            print("-" * 40)
            
            if isinstance(details, dict):
                for key, value in details.items():
                    if key not in ['raw_output', 'sample', 'error']:
                        if isinstance(value, bool):
                            icon = "✅" if value else "❌"
                            print(f"   {icon} {key.replace('_', ' ').title()}")
                        else:
                            print(f"   📋 {key.replace('_', ' ').title()}: {value}")
            
            if 'error' in details:
                print(f"   ❌ Error: {details['error']}")
        
        # Recommendations
        print("\n" + "="*80)
        print("💡 RECOMMENDATIONS")
        print("="*80)
        
        if self.status['overall_status'] == 'healthy':
            print("🎉 System is healthy and ready to run!")
            print("   Run: python start_flight_streaming.py")
        elif self.status['overall_status'] == 'warning':
            print("⚠️ System has some issues but may still work:")
            for check, passed in self.status['check_results'].items():
                if not passed:
                    print(f"   - Fix {check} issues")
        else:
            print("❌ System has critical issues that need to be fixed:")
            for check, passed in self.status['check_results'].items():
                if not passed:
                    print(f"   - Fix {check} issues")
        
        print("\n📚 For detailed setup instructions, see UNIFIED_SYSTEM_README.md")
        print("="*80)
    
    def save_status_report(self, filename='system_status.json'):
        """Save status report to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.status, f, indent=2, default=str)
        logger.info(f"Status report saved to {filename}")

def main():
    """Main function"""
    checker = SystemStatusChecker()
    checker.run_all_checks()
    checker.print_status_report()
    checker.save_status_report()
    
    # Exit with appropriate code
    if checker.status['overall_status'] == 'critical':
        sys.exit(1)
    elif checker.status['overall_status'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
