# 🛩️ Real-time Flight Monitoring and Analytics Platform

A comprehensive **enterprise-grade** data engineering pipeline implementing the **Lambda Architecture** pattern with:
- **Real-time layer**: Apache Flink for sub-second stream processing
- **Batch layer**: Apache Spark for scalable historical analytics
- **Storage**: AWS S3 (multi-layer data lake)
- **Analytics**: Snowflake (separation of compute & storage)
- **Orchestration**: Flexible (Custom + Dagster support)

## 🎯 Project Overview

This project demonstrates **production-ready** data engineering by implementing a hybrid streaming+batch architecture that:
- Ingests live flight data from OpenSky API
- Processes streams with **Flink** (real-time) and **Spark** (batch)
- Implements **Lambda Architecture**: separate speed and batch layers
- Uses multi-layer data lake (Bronze, Silver, Gold)
- Provides analytics-ready data in Snowflake
- Supports real-time dashboards and historical analytics

## 🏗️ Architecture

### **Lambda Architecture (Production-Ready)**

```
                     ┌──────────────────┐
                     │  OpenSky API     │
                     └────────┬─────────┘
                              │ fetches every 10s
                              ▼
                     ┌──────────────────┐
                     │ Kafka Producer   │
                     └────────┬─────────┘
                              │ streams
                              ▼
                     ┌──────────────────────────────────────────┐
                     │      Apache Kafka (realtime-flights)    │
                     └────────┬───────────────┬───────────────┘
                              │               │
           ╔════════════════╪═══════════════╪════════════════╗
           ║                │               │                ║
           ▼                ▼               ▼                ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │   Flink     │  │  Faust*     │  │   Spark     │  │  Dagster    │
    │  (Real-time)│  │  (Legacy)   │  │   (Batch)   │  │ (Orchestration)│
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │               │                │
           │  • Windowing   │  • Simple    │  • Large-scale │  • Scheduling
           │  • State       │  • Python    │  • ML/AI       │  • Monitoring
           │  • CEP         │  • Learning  │  • Aggregations│  • Asset tracking
           │  • Exactly-once│               │                │
           └────────┬───────┘               └────────┬───────┘
                    │                              │
                    └───────────┬──────────────────┘
                                │
              ┌─────────────────▼─────────────────┐
              │      AWS S3 (Bronze/Silver)       │
              │  Bronze: raw → Silver: cleaned   │
              └───────────────┬──────────────────┘
                              │ batch load
                              ▼
              ┌─────────────────────────────┐
              │      Snowflake (Gold)       │
              │  Real-time views +         │
              │  Historical analytics      │
              └───────────────┬─────────────┘
                              │ queries
                              ▼
              ┌─────────────────────────────┐
              │   Tableau / Dashboard       │
              └─────────────────────────────┘

*Faust is maintained for backward compatibility and learning purposes
```

### **Data Layers (Medallion Architecture)**

- **Bronze (Raw)**: Unmodified API responses in S3 (`s3://bucket/bronze/YYYY/MM/DD/HH/`)
- **Silver (Clean)**: Validated, deduplicated flight records (`s3://bucket/silver/`)
- **Gold (Analytics)**: Aggregated, business-ready tables in Snowflake
  - Real-time views (served by Flink)
  - Historical aggregates (served by Spark)

### **Technology Choices**

| Component | Current (Legacy) | Production (Recommended) | Why |
|-----------|-----------------|-------------------------|-----|
| **Stream Processing** | Faust (Python) | **Flink** (Java/Scala) | True streaming, stateful, CEP, exactly-once |
| **Batch Processing** | Pandas (single-node) | **Spark** (Scala/Python) | Distributed, MLlib, handles TB-scale |
| **Orchestration** | Custom Python | **Dagster** | Asset-aware, observability, scheduling |
| **Message Queue** | Kafka | Kafka | Industry standard, durable, scalable |
| **Data Lake** | S3 (JSON) | S3 (Parquet) | Columnar, compression, queryable |
| **Warehouse** | Snowflake | Snowflake | Separation of compute/storage |
| **Monitoring** | Console logs | **Prometheus + Grafana** | Metrics, alerts, dashboards |

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** (for legacy components)
- **Java 11+** (for Flink)
- **Scala/Spark** (for batch processing)
- **Docker & Docker Compose** (Kafka, Zookeeper)
- **AWS Account** with S3 access
- **Snowflake** account (for Gold layer)

### 1. Environment Setup
```bash
# Clone and setup
git clone <your-repo>
cd flight_pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment file
cp env_template.txt .env
# Edit .env with your AWS, Snowflake, and API credentials
```

### 2. Start Infrastructure
```bash
# Start Kafka stack
docker-compose up -d

# Verify services
docker-compose ps
# Expected: Kafka, Zookeeper, Schema Registry (if using)
```

### 3. Create AWS Resources
```bash
# Create S3 bucket with proper structure
aws s3 mb s3://realtimeflightstreamingbucket
aws s3api put-bucket-versioning --bucket realtimeflightstreamingbucket --versioning-configuration Status=Enabled
```

### 4. Run the Pipeline

#### **Option A: Legacy (Faust) - For Learning**
```bash
# Terminal 1: Producer
python OpenSky/flight-producer.py

# Terminal 2: Faust Stream Processor
python -m faust -A Faust.faust_app worker --loglevel=info --concurrency=1

# Terminal 3: ETL (Batch)
python Faust/bronze_to_silver.py  # runs once
python Faust/silver_to_gold.py    # runs once
```

#### **Option B: Production (Flink + Spark)**

**Start Real-time Layer (Flink):**
```bash
# Start Flink cluster (requires Java)
./flink/bin/start-cluster.sh

# Submit Flink job (Python API)
python OpenSky/flink_streaming_processor.py

# Or submit compiled JAR (Scala/Java)
./flink/bin/flink run -c com.flight.FlinkProcessor ./target/flight-processor.jar
```

**Start Batch Layer (Spark):**
```bash
# Submit Spark job (runs hourly/daily)
spark-submit \
  --master local[*] \
  --packages org.apache.hadoop:hadoop-aws:3.3.1 \
  Spark/spark_batch_processor.py \
  --date $(date -d "yesterday" +%Y-%m-%d)
```

**Orchestrated Execution (Recommended):**
```bash
# Start Dagster for scheduling
dagster dev -f dagster_app/defs.py

# Or use the unified orchestrator
python flight_streaming_orchestrator.py
# Then in interactive mode: start flink, start spark, monitor
```

## 📁 Project Structure

```
flight_pipeline/
├── OpenSky/                          # Data ingestion
│   ├── flight_producer.py           # Kafka producer (current)
│   ├── flight_kafka_consumer_to_s3.py  # S3 consumer (legacy)
│   ├── flink_streaming_processor.py # Flink streaming (new)
│   └── flink_flight_consumer.py     # Flink prototype (archived)
│
├── Faust/                            # Stream Processing (Legacy)
│   ├── faust_app.py                 # Faust worker (for learning)
│   ├── bronze_to_silver.py          # ETL: Bronze → Silver
│   ├── silver_to_gold.py            # ETL: Silver → Gold
│   ├── transformation_utils.py      # Pure transformation functions
│   └── analytics_dashboard.py       # Console analytics viewer
│
├── Spark/                            # Batch Processing (New ✨)
│   ├── spark_batch_processor.py     # Main Spark job
│   ├── spark_streaming_processor.py # Structured Streaming (optional)
│   ├── transformations/
│   │   ├── aggregations.py          # Daily/hourly aggregations
│   │   ├── enrichments.py           # Data enrichment logic
│   │   └── ml_features.py           # ML feature engineering
│   ├── utils/
│   │   ├── spark_utils.py           # Spark session, config
│   │   └── s3_utils.py              # S3 read/write optimizations
│   └── config.json                  # Spark-specific configuration
│
├── Flink/                            # Real-time Processing (New ✨)
│   ├── src/main/java/               # Java/Scala Flink jobs
│   │   └── com/flight/
│   │       ├── FlinkStreamProcessor.java
│   │       ├── WindowingAggregations.java
│   │       └── FlinkCEPAlerts.java
│   ├── src/main/python/             # PyFlink alternative
│   │   └── flink_streaming_processor.py
│   ├── conf/
│   │   ├── flink-conf.yaml          # Flink cluster config
│   │   └── log4j.properties         # Logging config
│   └── lib/                         # Custom connectors, UDFs
│
├── schemas/                          # Data validation
│   ├── flight_schema.py             # Pydantic models
│   ├── avro_schemas/                # Avro schemas for Schema Registry
│   └── expectations/                # Great Expectations suites
│
├── dagster_app/                     # Orchestration
│   ├── assets/
│   │   ├── ingestion.py             # Bronze ingestion asset
│   │   ├── silver.py                # Silver transformation asset
│   │   └── gold.py                  # Gold loading asset
│   ├── resources/
│   │   ├── s3_resource.py           # S3 connection resource
│   │   ├── snowflake_resource.py    # Snowflake resource
│   │   └── flink_resource.py        # Flink cluster resource (new)
│   └── defs.py                      # Dagster definitions
│
├── monitoring/                      # Observability
│   ├── prometheus/
│   │   ├── exporters/
│   │   │   ├── flink_exporter.py    # Flink metrics to Prometheus
│   │   │   ├── spark_exporter.py    # Spark metrics to Prometheus
│   │   │   └── custom_metrics.py    # Business metrics
│   │   └── dashboards/
│   │       ├── flink_grafana.json   # Flink Grafana dashboard
│   │       └── spark_grafana.json   # Spark Grafana dashboard
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── dashboards/
│   │   │   └── datasources/
│   │   └── dashboards/
│   └── alerting/
│       ├── alert_rules.yml          # Prometheus alert rules
│       └── routes.yml               # Alert routing (PagerDuty)
│
├── tests/                           # Test suite
│   ├── unit/
│   │   ├── test_flight_producer.py
│   │   ├── test_flink_processor.py  # New: Flink unit tests
│   │   ├── test_spark_batch.py      # New: Spark tests
│   │   └── integration/
│   │       ├── test_kafka_integration.py
│   │       ├── test_flink_integration.py
│   │       └── test_spark_integration.py
│   └── fixtures/
│       ├── sample_flights.json
│       └── flink_test_containers.py
│
├── docs/                            # Documentation
│   ├── architecture/
│   │   ├── lambda_architecture.md   # Lambda architecture details
│   │   ├── flink_design.md          # Flink job design
│   │   ├── spark_design.md          # Spark job design
│   │   └── data_flows.md            # End-to-end data flow diagrams
│   ├── operations/
│   │   ├── deployment.md            # Deployment guide
│   │   ├── troubleshooting.md       # Runbooks
│   │   ├── monitoring.md            # Monitoring setup
│   │   └── disaster_recovery.md     # DR procedures
│   └── api/                         # API documentation
│       ├── flink_rest_api.md        # Flink REST API reference
│       └── spark_rest_api.md
│
├── infrastructure/                  # Infra as Code
│   ├── terraform/
│   │   ├── main.tf                  # AWS infrastructure
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── kubernetes/
│   │   ├── flink-cluster.yaml       # Flink K8s deployment
│   │   ├── spark-job.yaml           # Spark on K8s
│   │   └── monitoring-stack.yaml    # Prometheus+Grafana
│   └── ansible/                     # Configuration management
│       ├── playbooks/
│       └── inventories/
│
├── scripts/                         # Utility scripts
│   ├── deploy/
│   │   ├── deploy_flink.sh
│   │   ├── deploy_spark.sh
│   │   └── rollback.sh
│   ├── maintenance/
│   │   ├── backup_s3.py
│   │   ├── vacuum_snowflake.py
│   │   └── clean_old_data.py
│   └── data/
│       ├── backfill.py              # Backfill missing data
│       └── validate_lineage.py      # Lineage verification
│
├── config/                          # Configuration templates
│   ├── flink/
│   │   ├── flink-conf.yaml.template
│   │   └── k8s-jobmanager.yaml.template
│   ├── spark/
│   │   ├── spark-defaults.conf.template
│   │   └── spark-env.sh.template
│   └── monitoring/
│       ├── prometheus.yml.template
│       └── grafana.ini.template
│
├── .env                             # Secrets (not in git)
├── .env.example                     # Example secrets
├── docker-compose.yml               # Kafka + Zookeeper + Schema Registry
├── docker-compose.monitoring.yml    # Prometheus + Grafana
├── requirements.txt                 # Python dependencies
├── requirements-dev.txt             # Dev dependencies (includes pyspark, flink)
├── pyproject.toml                   # Linting, formatting, type checking
├── Makefile                         # Standardized commands
├── start_flight_streaming.py        # Quick start (legacy)
├── flight_streaming_orchestrator.py # Custom orchestrator (legacy)
├── streaming_config.py              # Centralized configuration
├── run_complete_pipeline.py         # Manual ETL trigger
├── ENTERPRISE_READINESS_ASSESSMENT.md
├── UNIFIED_SYSTEM_README.md
├── CODEBASE_GUIDE.md
├── PROJECT_TRACKER.md
├── ARCHITECTURE_DECISION_RECORDS/   # ADRs (new)
│   ├── 001-lambda-architecture.md
│   ├── 002-flink-over-faust.md
│   ├── 003-spark-for-batch.md
│   └── 004-parquet-over-json.md
└── README.md                        # This file
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
  "velocity": 161.18,
  "processed_at": "2024-01-01T12:00:00Z",
  "ingestion_layer": "realtime"  // or "batch" for Spark results
}
```

### **Layer-Specific Schemas**

**Bronze Layer** (raw):
- Exact copy of API response
- Minimal transformation (format conversion only)
- Includes metadata: `fetch_timestamp`, `source`

**Silver Layer** (validated):
- Enforced schema via Pydantic
- Geographic filtering applied
- Null handling, type conversions
- Deduplication by `icao24 + time_position`

**Gold Layer** (analytics):
- **Real-time view**: Flight positions by minute
- **Batch aggregates**: Daily/hourly rollups, routes, airline metrics
- **Enriched data**: Weather, airport info (optional)

## 🔄 Lambda Architecture Explained

This project implements **Nathan Marz's Lambda Architecture** with three layers:

### 1. **Batch Layer** (Batch Processing - Spark)
- **Source**: All historical data in S3 Bronze
- **Processing**: Apache Spark (distributed, fault-tolerant)
- **Output**: Comprehensive aggregations, slow-changing dimensions
- **Frequency**: Hourly or daily (t+1 for complex aggregations)
- **Benefits**: 
  - Can reprocess entire history (correctness)
  - Handles complex joins and ML models
  - Cost-effective for large datasets
- **Use cases**:
  - Daily flight statistics per airline
  - Route popularity rankings
  - Historical anomaly detection models

### 2. **Speed Layer** (Real-time Processing - Flink)
- **Source**: Live Kafka stream
- **Processing**: Apache Flink (windowed aggregations, CEP)
- **Output**: Recent data views (last few minutes/hours)
- **Latency**: Sub-second to seconds
- **Benefits**:
  - Low-latency insights
  - Exactly-once semantics
  - Stateful stream processing (tumbling/sliding windows)
- **Use cases**:
  - Live dashboards (current flights, alerts)
  - Real-time anomaly detection (unusual speed/altitude)
  - Geofencing (flights entering restricted areas)

### 3. **Serving Layer** (Snowflake)
- **Merge** outputs from batch and speed layers
- **Design**: 
  - Real-time tables (updated by Flink)
  - Historical tables (updated by Spark)
  - ** Views** combine both for "complete" picture
- **Example**: 
  - `flights_current` (last 24h from Flink)
  - `flights_historical` (all time from Spark)
  - `flights_complete` (UNION ALL view)

### **Why Lambda (vs Kappa)?**

| Aspect | Lambda (Flink+Spark) | Kappa (Flink-only) |
|--------|---------------------|-------------------|
| **Complexity** | Higher (2 systems) | Lower (1 system) |
| **Historical reprocessing** | Easy (batch layer) | Hard (replay all time) |
| **Cost** | Lower (batch cheaper) | Higher (stream for everything) |
| **Latency for batch** | Low (pre-computed) | High (replay + recompute) |
| **When to choose** | >1 year history, rehydration needs | Pure real-time, no batch needs |

**Our choice**: Lambda because:
- We need both live AND historical analytics
- Batch recompute of 1-year data is expensive in pure streaming
- Different optimization strategies (cost vs latency)
- We can serve both dashboards from same Snowflake layer

## 🎯 Implementation Roadmap

### **Phase 1: Foundation (Current - Legacy)** ✅
- [x] Kafka setup with Faust (proof of concept)
- [x] Bronze layer (raw data to S3)
- [x] Basic ETL (Bronze → Silver → Gold)
- [x] Snowflake integration
- [x] Pydantic schemas and data validation

### **Phase 2: Migration to Lambda Architecture** 🔄
- [ ] **Set up Flink cluster** (local/cluster mode)
- [ ] **Implement Flink streaming job**:
  - [ ] Windowing aggregations (5-min, 1-hour)
  - [ ] Stateful processing (state backend: RocksDB)
  - [ ] Checkpointing to S3 (fault tolerance)
  - [ ] Connectors: Kafka → S3/State → Snowflake
- [ ] **Implement Spark batch job**:
  - [ ] Read from S3 Bronze (Parquet format)
  - [ ] Daily/hourly aggregations (groupBy, window)
  - [ ] ML features extraction (optional)
  - [ ] Write to Snowflake Gold (replace ETL jobs)
- [ ] **Configure orchestration**:
  - [ ] Dagster sensors for Flink health checks
  - [ ] Dagster schedules for Spark (daily at 2AM)
  - [ ] Unified monitoring dashboard

### **Phase 3: Production Enhancements** 📈
- [ ] **Data format upgrade**: JSON → Parquet (compression, query optimization)
- [ ] **Schema Registry**: Confluent Schema Registry for Avro/Protobuf
- [ ] **Exactly-once semantics**: Configure Flink checkpoints, Kafka transactions
- [ ] **Backpressure handling**: Flink's built-in, monitor Kafka lag
- [ ] **Auto-scaling**: K8s HPA for Flink TaskManagers, Spark dynamic allocation

### **Phase 4: Observability & Governance** 📊
- [ ] **Metrics**: Prometheus exporters for Flink (metrics reporter), Spark (Dropwizard)
- [ ] **Tracing**: OpenTelemetry instrumentation across pipeline
- [ ] **Alerting**: Grafana dashboards + PagerDuty/Opsgenie
- [ ] **Data quality**: Great Expectations suites for batch, Flink validation operators
- [ ] **Lineage**: OpenLineage or DataHub integration
- [ ] **Retention policies**: S3 lifecycle rules, Kafka topic TTL, Snowflake retention

### **Phase 5: Advanced Analytics** 🚀
- [ ] **Real-time ML**: Flink ML or custom models (anomaly detection)
- [ ] **Batch ML**: Spark MLlib training (flight delay prediction)
- [ ] **Geospatial**: Flink CEP for geofencing alerts
- [ ] **Data sharing**: Snowflake Secure Data Sharing with stakeholders
- [ ] **Multi-region**: S3 cross-region replication, failover strategy

## 🧪 Testing Strategy

| Type | Tools | Coverage Target |
|------|-------|----------------|
| **Unit** | pytest, unittest, pytest-mock | 80% |
| **Integration** | Testcontainers (Kafka, Flink, Spark) | 60% |
| **End-to-End** | LocalStack (AWS), Docker Compose | 40% |
| **Performance** | locust, custom benchmarks | N/A |

**Test Structure**:
```
tests/
├── unit/
│   ├── test_flink_processor.py        # Flink transformations
│   ├── test_spark_batch.py            # Spark aggregations
│   ├── test_schemas.py                # Pydantic validation
│   └── test_transformations.py        # Pure functions
├── integration/
│   ├── test_kafka_integration.py      # Kafka roundtrip
│   ├── test_flink_integration.py      # Flink + Kafka
│   ├── test_spark_integration.py      # Spark + S3
│   └── test_snowflake_integration.py  # Snowflake load
└── fixtures/
    ├── sample_flights_1k.json
    ├── sample_flights_10k.json
    └── testcontainers_setup.py
```

**Run tests**:
```bash
# All unit tests with coverage
make test

# Integration tests (requires Docker)
make test-integration

# Specific module
pytest tests/unit/test_flink_processor.py -v
```

## 🔒 Security Considerations

### **Data Protection**
- **Encryption at rest**: S3 SSE-S3 or SSE-KMS, Snowflake encryption
- **Encryption in transit**: TLS for Kafka, HTTPS for APIs, SSL for Snowflake
- **Secrets**: Use HashiCorp Vault or AWS Secrets Manager (not .env in production)
- **IAM roles**: Use instance profiles (EC2/ECS) instead of access keys

### **Access Control**
- **Kafka**: SASL_SSL + ACLs
- **S3**: Bucket policies, IAM roles with least privilege
- **Snowflake**: RBAC, MFA, network policies
- **Cluster**: Security groups, VPC endpoints

### **Compliance**
- GDPR: Data deletion procedures, consent tracking
- Audit logging: CloudTrail, Snowflake QUERY_HISTORY
- Data residency: Region-specific buckets

## 📈 Monitoring & Alerting

### **Metrics Collection**
- **Flink**: `Reporter` → Prometheus (metrics: uptime, buffer, latency)
- **Spark**: `DropwizardMetricsSink` → Prometheus (executor, shuffle, HDFS)
- **Kafka**: JMX exporter → Prometheus (lag, throughput, consumer lag)
- **Custom**: Business KPIs (flights/minute, alert counts)

### **Grafana Dashboards**
1. **Pipeline Health** (overview)
   - Jobs running/failed
   - End-to-end latency (p50, p95, p99)
   - Throughput (events/sec)
   - Error rates

2. **Flink Deep Dive**
   - Checkpoint duration/size
   - Taskmanager memory/CPU
   - Watermark lag
   - State size

3. **Spark Performance**
   - Stage durations
   - Shuffle read/write
   - Executor utilization
   - GC time

4. **Business Metrics**
   - Flights by country
   - Top airlines
   - Alert counts (geofence violations)

### **Alerting Rules** (Prometheus)
```yaml
groups:
  - name: flink_alerts
    rules:
      - alert: FlinkJobFailed
        expr: flink_job_uptime_seconds == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Flink job {{ $labels.job_name }} is down"

  - name: spark_alerts
    rules:
      - alert: SparkExecutorLost
        expr: spark_executor_uptime_seconds == 0
        for: 2m
        labels:
          severity: warning
```

## 🔄 Migration Path: Faust → Flink + Spark

**Step 1: Parallel Run** (Week 1-2)
- Keep Faust running (no changes)
- Deploy Flink in parallel (reads same Kafka topic)
- Compare outputs (Flink vs Faust) for validation

**Step 2: Gradual Cutover** (Week 3-4)
- Route 10% traffic to Flink (via separate Kafka topic)
- Increase to 50%, then 100%
- Decommission Faust after 2 weeks of stability

**Step 3: Batch Migration** (Week 5-6)
- Replace `bronze_to_silver.py` with Spark batch job
- Keep Pandas version for fallback
- Validate results match (row counts, aggregates)

**Step 4: Full Production** (Week 7-8)
- Remove Faust code (archive to `legacy/`)
- Optimize Flink/Spark configs
- Implement auto-scaling
- Set up comprehensive monitoring

**Rollback Plan**:
- If Flink fails: Switch Kafka consumer back to Faust
- If Spark fails: Re-run Pandas batch manually
- Maintain both for 4 weeks post-cutover

## 🎯 When to Use Which Layer

| Use Case | Flink (Real-time) | Spark (Batch) |
|----------|-------------------|---------------|
| Live dashboard (current flights) | ✅ | ❌ |
| Anomaly detection (seconds) | ✅ | ❌ |
| Geofencing alerts | ✅ | ❌ |
| Daily flight statistics | ⚠️ (possible) | ✅ (better) |
| Monthly revenue reports | ❌ | ✅ |
| ML model training | ❌ | ✅ |
| Backfill/Reprocess history | ❌ | ✅ |
| Complex joins (10+ tables) | ❌ | ✅ |
| Data quality validation | ✅ (streaming) | ✅ (batch) |
| Regulatory reports (monthly) | ❌ | ✅ |

**Rule of thumb**:
- **Flink**: latency < 1 minute, stateful, event-driven
- **Spark**: latency > 5 minutes, large data, complex transformations

## 🤝 Contributing

This is a **learning project** demonstrating enterprise data engineering. We welcome:

1. **Architecture improvements**: Alternative patterns (Kappa, Data Mesh)
2. **Code contributions**: Implement Flink/Spark jobs, add tests
3. **Documentation**: Clarify concepts, add diagrams
4. **Production hardening**: Security, monitoring, CI/CD
5. **Performance tuning**: Benchmarking, optimization studies

**Development workflow**:
```bash
git checkout -b feature/flink-windowing
# Make changes, add tests
pytest tests/
# Ensure 80%+ coverage
make lint
# Open PR with architecture diagram
```

## 📚 Further Reading

### **Lambda Architecture**
- [Nathan Marz's Lambda Architecture](http://nathanmarz.com/blog/how-to-beat-the-cap-theorem.html)
- [Lambda Architecture in Practice (O'Reilly)](https://www.oreilly.com/ideas/lambda-architecture)

### **Flink**
- [Apache Flink Documentation](https://flink.apache.org/docs/stable/)
- [Streaming Systems by Tyler Akidau](https://www.oreilly.com/library/view/streaming-systems/9781491893961/)
- [Stateful Stream Processing with Flink](https://flink.apache.org/stateful-stream-processing.html)

### **Spark**
- [Spark: The Definitive Guide (O'Reilly)](https://www.oreilly.com/library/view/spark-the-definitive/9781491911434/)
- [Spark SQL, DataFrames, and Datasets Guide](https://spark.apache.org/docs/latest/sql-programming-guide.html)

### **Data Engineering**
- [Designing Data-Intensive Applications (Martin Kleppmann)](https://dataintensive.net/)
- [Fundamentals of Data Engineering](https://www.oreilly.com/library/view/fundamentals-of-data/9781492092384/)

---

**Ready to start?** Run `python setup_project.py` and follow the prompts!

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