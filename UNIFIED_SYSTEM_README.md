# 🛩️ Unified Real-time Flight Streaming System

A comprehensive, production-ready data engineering pipeline that processes live aircraft telemetry data in real-time using modern streaming technologies.

## 🎯 System Overview

This unified system integrates all pipeline components into one seamless real-time streaming platform:

```
OpenSky API → Kafka → Faust Stream Processing → AWS S3 (Bronze/Silver) → Snowflake (Gold) → Real-time Dashboard
```

### Key Features

- **Real-time Data Ingestion**: Live flight data from OpenSky API
- **Stream Processing**: Kafka + Faust for real-time data transformation
- **Multi-layer Data Architecture**: Bronze (raw) → Silver (clean) → Gold (analytics)
- **Cloud Storage**: AWS S3 for scalable data lake
- **Data Warehouse**: Snowflake for analytics and reporting
- **Monitoring**: Real-time pipeline health monitoring
- **Interactive Dashboard**: Live analytics and insights
- **Auto-scaling**: Configurable batch processing and ETL cycles

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker & Docker Compose
- AWS Account with S3 access
- Snowflake account
- Virtual environment (recommended)

### 1. Setup Environment

```bash
# Clone and navigate to project
cd flight_pipeline

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
# Copy template and edit
cp env_template.txt .env

# Edit .env with your credentials:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - SNOWFLAKE_USER
# - SNOWFLAKE_ACCOUNT
# - SNOWFLAKE_PRIVATE_KEY_PATH
# - SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
```

### 3. Start the Unified System

```bash
# Option 1: Quick start (recommended)
python start_flight_streaming.py

# Option 2: Manual orchestration
python flight_streaming_orchestrator.py

# Option 3: Check configuration first
python streaming_config.py
```

## 🏗️ System Architecture

### Components

1. **Data Ingestion Layer**
   - OpenSky API Producer (`OpenSky/flight-producer.py`)
   - Kafka Message Broker
   - Real-time data streaming

2. **Stream Processing Layer**
   - Faust Stream Processor (`Faust/faust_app.py`)
   - Real-time data transformation
   - Bronze to Silver processing

3. **Storage Layer**
   - AWS S3 Bronze Layer (raw data)
   - AWS S3 Silver Layer (cleaned data)
   - Snowflake Gold Layer (analytics-ready)

4. **Analytics Layer**
   - Real-time dashboard (`Faust/analytics_dashboard.py`)
   - Snowflake analytics views
   - Business intelligence ready

5. **Orchestration Layer**
   - Unified orchestrator (`flight_streaming_orchestrator.py`)
   - Health monitoring
   - Auto-restart capabilities

### Data Flow

```
1. OpenSky API → Raw flight data
2. Kafka Producer → Message queue
3. Faust Consumer → Stream processing
4. S3 Bronze → Raw data storage
5. ETL Process → Data cleaning
6. S3 Silver → Cleaned data
7. Snowflake ETL → Analytics transformation
8. Snowflake Gold → Analytics tables
9. Dashboard → Real-time insights
```

## 📊 Data Schema

### Flight Record Structure
```json
{
  "icao24": "801642",
  "callsign": "AXB1124", 
  "origin_country": "India",
  "time_position": 1753735222,
  "longitude": 75.8221,
  "latitude": 28.2676,
  "baro_altitude": 4892.04,
  "velocity": 161.18,
  "processed_at": "2024-01-01T12:00:00Z"
}
```

### Snowflake Tables

#### flights_raw
- Raw flight data with computed partition_date
- Clustered by date and country for performance

#### Analytics Views
- `daily_flight_counts`: Daily summaries by country
- `hourly_flight_activity`: Hourly flight patterns
- `top_airlines`: Top airlines by flight count

## 🎮 Interactive Commands

When running the unified system, you can use these commands:

```
status    - Show pipeline status
restart   - Restart all components
etl       - Run manual ETL cycle
dashboard - Show analytics dashboard
logs      - Show recent logs
stop      - Stop pipeline and exit
help      - Show available commands
```

## 🔧 Configuration

### Environment Variables

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-south-1
S3_BUCKET_NAME=realtimeflightstreamingbucket

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=realtime-flights

# Snowflake Configuration
SNOWFLAKE_USER=your_user
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/rsa_key.p8
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=your_passphrase

# OpenSky API Configuration
OPENSKY_API_URL=https://opensky-network.org/api/states/all
FETCH_INTERVAL_SECONDS=10
BATCH_SIZE=300

# Geographic bounds (India)
INDIA_BOUNDS=6.0,38.0,68.0,97.0
```

### Streaming Configuration

```python
STREAMING_CONFIG = {
    'producer_interval': 10,      # seconds
    'faust_workers': 1,           # number of workers
    'buffer_size': 1000,          # buffer size
    'etl_interval': 300,          # ETL cycle (5 minutes)
    'dashboard_interval': 30,     # dashboard update (30 seconds)
    'health_check_interval': 30,  # health check (30 seconds)
    'max_retries': 3,             # retry attempts
    'retry_delay': 5              # retry delay (seconds)
}
```

## 📈 Monitoring & Analytics

### Real-time Metrics
- Flight count by country
- Top airlines
- Average altitude and velocity
- Hourly activity patterns
- Geographic distribution

### Health Monitoring
- Pipeline component status
- Data flow rates
- Error rates and alerts
- Resource utilization
- ETL success/failure rates

### Logging
- Centralized logging to `flight_pipeline.log`
- Component-specific log levels
- Error tracking and alerting
- Performance metrics

## 🛠️ Troubleshooting

### Common Issues

1. **Kafka Connection Issues**
   ```bash
   # Check Docker services
   docker-compose ps
   
   # Restart services
   docker-compose restart
   ```

2. **Snowflake Connection Issues**
   ```bash
   # Test connection
   python Faust/temp.py
   
   # Check key-pair authentication
   # Verify SNOWFLAKE_PRIVATE_KEY_PATH
   ```

3. **AWS S3 Access Issues**
   ```bash
   # Verify credentials
   aws s3 ls s3://realtimeflightstreamingbucket
   
   # Check region settings
   ```

4. **ETL Failures**
   ```bash
   # Check logs
   tail -f flight_pipeline.log
   
   # Run manual ETL
   python Faust/bronze_to_silver.py
   python Faust/silver_to_gold.py
   ```

### Performance Tuning

1. **Kafka Tuning**
   - Adjust batch size and interval
   - Increase partition count for parallel processing
   - Tune memory settings

2. **Snowflake Tuning**
   - Use appropriate warehouse size
   - Implement clustering keys
   - Optimize query patterns

3. **Stream Processing Tuning**
   - Adjust buffer sizes
   - Increase worker count
   - Optimize ETL intervals

## 🔄 Deployment Options

### Development
```bash
python start_flight_streaming.py
```

### Production
```bash
# Use systemd service
sudo systemctl start flight-streaming

# Use Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Deployment
- AWS ECS/EKS for container orchestration
- AWS MSK for managed Kafka
- Snowflake for data warehouse
- CloudWatch for monitoring

## 📚 API Reference

### Orchestrator API
```python
from flight_streaming_orchestrator import FlightStreamingOrchestrator

orchestrator = FlightStreamingOrchestrator()
orchestrator.check_prerequisites()
orchestrator.start_streaming_pipeline()
orchestrator.monitor_pipeline()
```

### Configuration API
```python
from streaming_config import config

# Access configuration
aws_region = config.AWS_REGION
snowflake_config = config.SNOWFLAKE_CONFIG

# Validate configuration
validation = config.validate()
```

## 🎯 Next Steps

1. **Scale the System**
   - Add more Kafka partitions
   - Increase Faust workers
   - Implement auto-scaling

2. **Enhanced Analytics**
   - Add machine learning models
   - Implement anomaly detection
   - Create predictive analytics

3. **Visualization**
   - Connect to Tableau/PowerBI
   - Create real-time dashboards
   - Implement alerting systems

4. **Data Quality**
   - Add data validation rules
   - Implement schema evolution
   - Create data lineage tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Review the logs in `flight_pipeline.log`
- Create an issue in the repository

---

**Happy Streaming! 🛩️✨**
