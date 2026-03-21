#!/usr/bin/env python3
"""
⚙️ Flight Streaming System Configuration
Centralized configuration for the unified streaming pipeline
"""

import os
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class StreamingConfig:
    """Configuration class for the flight streaming system"""
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'realtimeflightstreamingbuckett')
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'realtime-flights')
    
    # OpenSky API Configuration
    OPENSKY_API_URL = os.getenv('OPENSKY_API_URL', 'https://opensky-network.org/api/states/all')
    FETCH_INTERVAL_SECONDS = int(os.getenv('FETCH_INTERVAL_SECONDS', '10'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '300'))
    
    # Geographic bounds (India)
    INDIA_BOUNDS = os.getenv('INDIA_BOUNDS', '6.0,38.0,68.0,97.0').split(',')
    
    # Snowflake Configuration
    SNOWFLAKE_CONFIG = {
        'user': os.getenv('SNOWFLAKE_USER'),
        'account': os.getenv('SNOWFLAKE_ACCOUNT'),
        'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
        'database': os.getenv('SNOWFLAKE_DATABASE', 'FLIGHT_ANALYTICS'),
        'schema': os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
        'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        'private_key_path': os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH'),
        'private_key_passphrase': os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE')
    }
    
    # Streaming Pipeline Configuration
    STREAMING_CONFIG = {
        'producer_interval': 10,  # seconds
        'faust_workers': 1,
        'buffer_size': 1000,
        'etl_interval': 300,  # 5 minutes
        'dashboard_interval': 30,  # seconds
        'health_check_interval': 30,  # seconds
        'max_retries': 3,
        'retry_delay': 5  # seconds
    }
    
    # Data Processing Configuration
    DATA_CONFIG = {
        'bronze_prefix': 'raw_flights/',
        'silver_prefix': 'silver_flights/',
        'gold_prefix': 'gold_flights/',
        'max_file_size': 100 * 1024 * 1024,  # 100MB
        'compression': 'gzip',
        'file_format': 'json'
    }
    
    # Monitoring Configuration
    MONITORING_CONFIG = {
        'log_level': 'INFO',
        'log_file': 'flight_pipeline.log',
        'metrics_enabled': True,
        'alert_threshold': {
            'error_rate': 0.1,  # 10%
            'latency_ms': 5000,  # 5 seconds
            'memory_usage': 0.8  # 80%
        }
    }
    
    @classmethod
    def validate(cls) -> Dict[str, bool]:
        """Validate configuration and return status"""
        validation = {
            'aws_credentials': bool(cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY),
            'snowflake_credentials': bool(cls.SNOWFLAKE_CONFIG['user'] and cls.SNOWFLAKE_CONFIG['account']),
            'snowflake_key': bool(cls.SNOWFLAKE_CONFIG['private_key_path']),
            'kafka_config': bool(cls.KAFKA_BOOTSTRAP_SERVERS),
            'geographic_bounds': len(cls.INDIA_BOUNDS) == 4
        }
        
        validation['overall'] = all(validation.values())
        return validation
    
     @classmethod
     def get_geographic_bounds(cls) -> Dict[str, float]:
         """Get geographic bounds as dictionary"""
         return {
             'min_lat': float(cls.INDIA_BOUNDS[0]),
             'max_lat': float(cls.INDIA_BOUNDS[1]),
             'min_lon': float(cls.INDIA_BOUNDS[2]),
             'max_lon': float(cls.INDIA_BOUNDS[3])
         }
     
     @classmethod
     def print_config(cls):
         """Print current configuration (without sensitive data)"""
         print("""
 ╔══════════════════════════════════════════════════════════════╗
 ║                    📋 CONFIGURATION STATUS                   ║
 ╚══════════════════════════════════════════════════════════════╝
         """)
         
         print("🔧 AWS Configuration:")
         print(f"   Region: {cls.AWS_REGION}")
         print(f"   S3 Bucket: {cls.S3_BUCKET_NAME}")
         print(f"   Access Key: {'✅ Set' if cls.AWS_ACCESS_KEY_ID else '❌ Missing'}")
         
         print("\n🔧 Kafka Configuration:")
         print(f"   Bootstrap Servers: {cls.KAFKA_BOOTSTRAP_SERVERS}")
         print(f"   Topic: {cls.KAFKA_TOPIC}")
         
         print("\n🔧 Snowflake Configuration:")
         print(f"   Account: {cls.SNOWFLAKE_CONFIG['account']}")
         print(f"   User: {cls.SNOWFLAKE_CONFIG['user']}")
         print(f"   Database: {cls.SNOWFLAKE_CONFIG['database']}")
         print(f"   Private Key: {'✅ Set' if cls.SNOWFLAKE_CONFIG['private_key_path'] else '❌ Missing'}")
         
         print("\n🔧 OpenSky API Configuration:")
         print(f"   URL: {cls.OPENSKY_API_URL}")
         print(f"   Fetch Interval: {cls.FETCH_INTERVAL_SECONDS}s")
         print(f"   Batch Size: {cls.BATCH_SIZE}")
         
         bounds = cls.get_geographic_bounds()
         print("\n🔧 Geographic Bounds (India):")
         print(f"   Latitude: {bounds['min_lat']} to {bounds['max_lat']}")
         print(f"   Longitude: {bounds['min_lon']} to {bounds['max_lon']}")
         
         # Validation status
         validation = cls.validate()
         print("\n🔧 Configuration Validation:")
         for key, status in validation.items():
             if key != 'overall':
                 icon = "✅" if status else "❌"
                 print(f"   {icon} {key.replace('_', ' ').title()}")
         
         print(f"\n{'='*60}")
         if validation['overall']:
             print("🎉 Configuration is valid and ready to run!")
         else:
             print("⚠️ Configuration has issues. Please fix the missing items above.")
         print("="*60)


# ============================================================================
# Future Configuration: Flink & Spark (Lambda Architecture)
# ============================================================================
# These settings will be used when migrating from Faust/Pandas to Flink/Spark.
# They are not actively used yet but defined here for planning purposes.

FLINK_CONFIG = {
    'checkpoint_interval': 60000,  # ms (60 seconds)
    'parallelism': 10,
    'state_backend': 'rocksdb',
    'checkpoint_dir': 's3://realtimeflightstreamingbuckett/flink-checkpoints/',
    'savepoint_dir': 's3://realtimeflightstreamingbuckett/flink-savepoints/',
    ' restart_strategy': 'exponential-delay',
    'restart_max_attempts': 3,
    'jobmanager_memory': '4096m',
    'taskmanager_memory': '8192m',
    'kafka_consumer_group_id': 'flink-speed-layer',
    'watermark_delay_seconds': 5,  # event time lateness
}

SPARK_CONFIG = {
    'app_name': 'FlightBatchProcessor',
    'master': 'local[*]',
    'executor_memory': '8g',
    'driver_memory': '4g',
    'dynamic_allocation_enabled': True,
    'min_executors': 2,
    'max_executors': 20,
    'shuffle_partitions': 200,
    'sql_adaptive_enabled': True,
    'parquet_compression': 'snappy',
    'batch_schedule_cron': '0 2 * * *',  # Daily at 2 AM
    's3_silver_path': 's3://realtimeflightstreamingbuckett/silver_flights/',
    'snowflake_table': 'FLIGHTS_DAILY_AGG',
}

# Global configuration instance
config = StreamingConfig()

if __name__ == "__main__":
    config.print_config()
