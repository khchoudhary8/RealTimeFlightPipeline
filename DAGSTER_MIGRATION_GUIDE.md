# 🚀 Migration: Custom Orchestrator → Dagster

## Summary

**Replaced** the custom `flight_streaming_orchestrator.py` with **Dagster** for production-grade orchestration.

**Date**: 2025-03-19
**Status**: ✅ Complete

---

## 📋 What Changed

### **Removed (Old System)**
- ❌ `flight_streaming_orchestrator.py` (587 lines custom orchestration)
- ❌ `start_flight_streaming.py` (102 lines startup script)
- ❌ `run_complete_pipeline.py` (manual ETL trigger)
- ❌ `quick_status_check.py`, `check_system_status.py` (redundant status scripts)

### **Added (New Dagster System)**
- ✅ `dagster_app/` - **Production-ready assets** (ingestion, silver, gold)
- ✅ `dagster.yaml` - Dagster configuration
- ✅ `dagster_start.py` - Single command to start everything
- ✅ `dagster_trigger_etl.py` - Manual ETL trigger
- ✅ **Scheduling** - Automatic hourly ETL runs
- ✅ **Asset tracking** - Know exactly what data exists and when it was created
- ✅ **Observability** - Dagster UI for monitoring and debugging

---

## 🎯 Benefits of Dagster

| Feature | Old (Custom) | New (Dagster) |
|---------|--------------|---------------|
| **Scheduling** | Manual/Cron | Built-in cron scheduler |
| **Asset Tracking** | None | Complete lineage & metadata |
| **Observability** | Print statements only | Web UI with logs, metrics, DAG |
| **Retry Logic** | None | Automatic retries on failure |
| **Alerting** | None | Can integrate with PagerDuty, Slack |
| **Code Quality** | Mixed logic | Asset-based, testable, reusable |
| **Error Handling** | Basic | Rich context, materialization history |
| **Resource Management** | Global variables | Configurable resources (S3, Snowflake) |

---

## 🚀 How to Start the Pipeline

### **Quick Start (3 Steps)**

**Terminal 1** - Start infrastructure and data producer:
```bash
python dagster_start.py
```
This starts:
- Kafka + Zookeeper (Docker)
- Flight producer (OpenSky API → Kafka)

**Terminal 2** - Start Dagster daemon:
```bash
dagster-daemon run -f dagster_app/defs.py
```

**Terminal 3** - Start Dagster web UI:
```bash
dagster dev -f dagster_app/defs.py
# OR
dagster dev -f dagster_app/defs.py --load-requirements=requirements.txt
```

Then open: **http://localhost:3000**

### **Trigger ETL Manually**

Once Dagster UI is running:
```bash
python dagster_trigger_etl.py
```

Or from the UI:
1. Go to http://localhost:3000
2. Click on "Jobs" → "etl_pipeline"
3. Click "Launch Run"

### **Automatic Scheduling**

ETL runs **automatically every hour** (on the hour) via Dagster schedule.

Check schedule status in UI → "Schedules" tab.

---

## 🏗️ Architecture

```
OpenSky API
    ↓
flight_producer.py (standalone process)
    ↓ (Kafka: realtime-flights)
Kafka
    ↓
[bronze_flight_files] (Dagster asset)
    ↓
[silver_flights] (Dagster asset)
    ├─> Reads bronze S3 files
    ├─> Validates with Pydantic
    ├─> Writes Delta Lake (S3)
    └─> Moves processed files
    ↓
[gold_flights] (Dagster asset)
    ├─> Loads to Snowflake
    └─> Creates analytical views
```

---

## 📊 Assets in Dagster

### **1. bronze_flight_files**
- **Type**: Asset
- **Description**: List of JSON files in S3 bronze layer
- **Partitioned**: No
- **Materialization**: Every time it's evaluated

### **2. silver_flights**
- **Type**: Asset
- **Description**: Cleaned flight data in Delta Lake format
- **Partitioned**: Yes (by `partition_date`)
- **Materialization**: When bronze files change or manually triggered
- **Output**: `s3://bucket/silver_flights/YYYY/MM/DD/HH/`

### **3. gold_flights**
- **Type**: Asset
- **Description**: Flight data loaded to Snowflake + analytical views
- **Depends on**: `silver_flights`
- **Materialization**: After silver layer updates
- **Output**: Snowflake table `FLIGHTS_RAW` + views

---

## 🔧 Configuration

### **Environment Variables** (`.env`)

Required for full pipeline:
```bash
# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-south-1
S3_BUCKET_NAME=realtimeflightstreamingbucket

# Snowflake
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password  # Or use private key
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=FLIGHT_ANALYTICS
SNOWFLAKE_SCHEMA=PUBLIC
```

### **Dagster Configuration** (`dagster.yaml`)

Default configuration:
- Storage: SQLite (`.dagster/storage`)
- Scheduling: Hourly cron
- Telemetry: Disabled

For production, replace SQLite with PostgreSQL:
```yaml
storage:
  postgres:
    postgres_db:
      username: dagster
      password: dagster_password
      hostname: localhost
      db_name: dagster
      port: 5432
```

---

## 🧪 Testing Dagster Locally

### **Check Asset Materializations**
```bash
# List all assets
dagster asset list -f dagster_app/defs.py

# Materialize specific asset
dagster asset materialize -f dagster_app/defs.py -a bronze_flight_files

# Materialize all downstream
dagster asset materialize -f dagster_app/defs.py -a bronze_flight_files --select-downstream
```

### **View Run History**
```bash
dagster job list -f dagster_app/defs.py
dagster job runs -j etl_pipeline
```

### **Debug Failed Runs**
```bash
dagster job logs -f dagster_app/defs.py -j etl_pipeline -r RUN_ID
```

---

## 📈 Monitoring & Observability

### **Dagster UI** (http://localhost:3000)
- **Jobs**: View etl_pipeline runs, history, status
- **Assets**: See materialization history, lineage
- **Schedules**: Check next run time, past runs
- **Runs**: Live logs, duration, results

### **Logs**
Dagster daemon logs are in the terminal where you ran `dagster-daemon run`.

For persistent logs, configure in `dagster.yaml`:
```yaml
logging:
  python_log_level: INFO
  dagster_handler_level: INFO
```

---

## 🔄 Differences from Old System

| Old System | New Dagster |
|------------|-------------|
| `flight_streaming_orchestrator.py` interactive CLI | Dagster UI + CLI |
| Status commands (`status`, `etl`, `dashboard`) | Asset materializations & job runs |
| Manual ETL via `run_complete_pipeline.py` | Scheduled + manual trigger |
| No asset tracking | Full lineage & metadata |
| Custom health checks | Built-in health monitoring |
| Print-based logging | Structured logs + UI integration |

---

## 🐛 Troubleshooting

### **Dagster daemon won't start**
```bash
# Check if Dagster is installed
dagster --version

# Check dagster.yaml syntax
dagster-daemon validate -f dagster_app/defs.py

# Start daemon with verbose logging
dagster-daemon run -f dagster_app/defs.py -l debug
```

### **Assets not materializing**
- Check daemon is running: `dagster-daemon status`
- Check schedule is enabled in UI → "Schedules"
- Check `bronze_flight_files` has new data (S3 files)
- View asset_details in UI for specific errors

### **Snowflake connection errors**
- Verify `.env` has all required variables
- Test connection: `python -c "import snowflake.connector; conn = snowflake.connector.connect(...)"`
- Check network/firewall allows Snowflake access

### **Kafka not reachable**
- Ensure Docker services running: `docker-compose ps`
- Check producer is running (from `dagster_start.py`)
- Verify Kafka topic exists: `kafka-topics --bootstrap-server localhost:9092 --list`

---

## 🎯 Production Deployment

For production, use:

1. **Dagster Cloud** (recommended) or **self-hosted** with:
   - PostgreSQL storage (instead of SQLite)
   - Redis for queues
   - gunicorn/nginx for webserver
   - systemd services for daemon

2. **Infrastructure as Code**:
   ```bash
   # Terraform for S3, Snowflake, EC2/K8s
   terraform apply
   ```

3. **Monitoring**:
   - Prometheus metrics from Dagster
   - Grafana dashboards
   - Alerting on job failures

4. **Secrets Management**:
   - AWS Secrets Manager or HashiCorp Vault
   - Inject into Dagster as environment variables

---

## 📚 References

- [Dagster Documentation](https://docs.dagster.io/)
- [Dagster Assets](https://docs.dagster.io/concepts/assets/asset-fundamentals)
- [Dagster Schedules](https://docs.dagster.org/concepts/partitions-schedules-sensors/schedules)
- [Dagster Resources](https://docs.dagster.org/guides/dagster/pythonic_resources/)

---

## 🤝 Support

**Issues?**
1. Check `dagster_start.py` output
2. Check Dagster UI http://localhost:3000
3. View logs in terminal where daemon runs
4. Check `dagster.yaml` configuration

**Need help?**
- Read the docs links above
- Search Dagster community Slack
- Create issue in this repository

---

**Migration completed!** You now have a professional, scalable orchestration platform. 🎉
