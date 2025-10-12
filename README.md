# 🛩️ Real-time Flight Monitoring and Analytics Platform

A comprehensive data engineering pipeline that processes live aircraft telemetry data using Kafka, Faust, AWS S3, and Snowflake.

## 🎯 Project Overview

This project demonstrates modern data engineering practices by building a real-time streaming pipeline that:
- Ingests live flight data from OpenSky API
- Processes data streams using Kafka and Faust
- Implements a multi-layer data lake architecture (Bronze, Silver, Gold)
- Provides analytics-ready data in Snowflake
- Enables real-time dashboards via Tableau

## 🏗️ Architecture

```
OpenSky API → Kafka Producer → Kafka → Faust Processing → AWS S3 (Bronze/Silver) → Snowflake (Gold) → Tableau
```

### Data Layers:
- **Bronze (Raw)**: Unmodified API responses stored in S3
- **Silver (Clean)**: Filtered and deduplicated data
- **Gold (Analytics)**: Aggregated, business-ready data in Snowflake

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Docker & Docker Compose
- AWS Account with S3 access
- Snowflake account (for Gold layer)

### 1. Environment Setup
```bash
# Run the setup script
python setup_project.py

# Edit .env file with your credentials
cp config_template.env .env
# Edit .env with your AWS and Snowflake credentials
```

### 2. Start Infrastructure
```bash
# Start Kafka and Zookeeper
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 3. Create AWS Resources
```bash
# Create S3 bucket (replace with your preferred name)
aws s3 mb s3://realtimeflightstreamingbucket
```

### 4. Run the Pipeline

#### Option A: Basic Kafka Pipeline
```bash
# Terminal 1: Start producer
python OpenSky/flight-producer.py

# Terminal 2: Start consumer
python OpenSky/flight_kafka_consumer_to_s3.py
```

#### Option B: Faust Stream Processing
```bash
# Start Faust app
python -m faust -A Faust.faust_app worker --loglevel=info
```

## 📁 Project Structure

```
flight_pipeline/
├── OpenSky/                    # Data ingestion components
│   ├── flight-producer.py      # Kafka producer
│   ├── flight_kafka_consumer_to_s3.py  # S3 consumer
│   └── flink_flight_consumer.py (optional)
├── Faust/                      # Stream processing
│   ├── faust_app.py           # Faust stream processor
│   └── bronze_to_silver.py    # Data transformation
├── docker-compose.yml         # Kafka infrastructure
├── requirements.txt           # Python dependencies
├── setup_project.py          # Setup automation
└── config_template.env       # Configuration template
```

## 🔧 Configuration

Key configuration in `.env`:
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=realtimeflightstreamingbucket

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=realtime-flights

# Geographic bounds (India)
INDIA_BOUNDS=6.0,38.0,68.0,97.0
```

## 📊 Data Schema

### Flight Record Structure:
```json
{
  "icao24": "801642",
  "callsign": "AXB1124", 
  "origin_country": "India",
  "time_position": 1753735222,
  "longitude": 75.8221,
  "latitude": 28.2676,
  "baro_altitude": 4892.04,
  "velocity": 161.18
}
```

## 🎯 Implementation Roadmap

### Phase 1: Foundation ✅
- [x] Kafka setup and basic producer/consumer
- [x] Bronze layer (raw data to S3)
- [x] Basic environment configuration

### Phase 2: Stream Processing 🔄
- [ ] Enhanced Faust processing
- [ ] Improved Silver layer transformation
- [ ] Data quality checks and monitoring

### Phase 3: Analytics Layer 📈
- [ ] Snowflake integration
- [ ] Gold layer tables
- [ ] Data aggregations and metrics

### Phase 4: Visualization 📊
- [ ] Tableau dashboard setup
- [ ] Real-time monitoring views
- [ ] Business intelligence reports

## 🛠️ Troubleshooting

### Common Issues:

1. **Kafka Connection Issues**
   ```bash
   # Check if services are running
   docker-compose ps
   
   # Restart services
   docker-compose down && docker-compose up -d
   ```

2. **AWS Permission Errors**
   - Verify AWS credentials in `.env`
   - Ensure S3 bucket exists and has proper permissions

3. **Python Dependencies**
   ```bash
   # Reinstall requirements
   pip install -r requirements.txt
   ```

## 📈 Monitoring

Monitor your pipeline:
- Check Kafka topics: `docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092`
- View S3 objects: `aws s3 ls s3://your-bucket-name/bronze/ --recursive`
- Monitor Faust workers: Check console logs for processing statistics

## 🔄 Next Steps

1. **Complete Phase 1**: Ensure basic pipeline is working
2. **Enhance Stream Processing**: Improve Faust application
3. **Implement Silver Layer**: Clean and deduplicate data
4. **Set up Snowflake**: Create Gold layer tables
5. **Build Dashboards**: Connect Tableau to Snowflake

## 🤝 Contributing

This is a learning project demonstrating data engineering skills. Feel free to:
- Add new features
- Improve error handling
- Enhance monitoring
- Add tests

## 📝 Skills Demonstrated

- **Stream Processing**: Kafka, Faust
- **Cloud Storage**: AWS S3, partitioning strategies
- **Data Warehousing**: Snowflake, schema design
- **Data Engineering**: ETL pipelines, data quality
- **DevOps**: Docker, environment management
- **Analytics**: Data modeling, dashboard design

---

**Ready to start?** Run `python setup_project.py` and follow the prompts!