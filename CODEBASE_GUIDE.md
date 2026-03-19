# 🗺️ Flight Pipeline - Complete Codebase Map

## 🎯 **What Is This Project?**

**Real-time Flight Monitoring & Analytics Platform**
- Fetches live flight data from OpenSky API
- Streams through Kafka
- Processes and transforms data (Bronze → Silver → Gold)
- Loads into Snowflake for analytics
- Provides dashboards and insights

**Architecture (Current):**
```
OpenSky API → Producer → Kafka → Faust Stream Processing → S3 → Snowflake → Dashboard
```

**Architecture (Target - Lambda Pattern):**
```
OpenSky API → Producer → Kafka
                        ├── Flink (Real-time) → S3 Silver (streaming aggregates)
                        └── Spark (Batch) → S3 Silver → Gold (historical aggregates)
                                                ↓
                                         Snowflake (Unified View) → Dashboard
```

**Key Evolution:**
- **Flink** replaces Faust for production-grade streaming (sub-second latency, exactly-once, stateful)
- **Spark** replaces Pandas for distributed batch processing (TB-scale, MLlib)
- **Parquet** replaces JSON for columnar storage (compression, query performance)
- **Dagster** provides production orchestration (scheduling, asset tracking, alerts)

---

**Technology Maturity:**
- ✅ **Complete**: Kafka, S3, Snowflake, Dagster
- 🔄 **Migration in Progress**: Faust → Flink
- ❌ **Missing**: Spark batch layer, Flink production deployment

---

## 📁 **Directory Structure Explained**

### **1. `OpenSky/` - Data Ingestion**
**Purpose**: Get flight data from external API and push to Kafka

#### Files:
- **`flight_producer.py`** (MAIN)
  - Continuously fetches flight data from OpenSky API
  - Filters for flights over India
  - Sends to Kafka topic `realtime-flights`
  - ✅ **Well-tested** (8 tests, 97% coverage)
  - ⭐ **Good example** of testable design

- **`flight_kafka_consumer_to_s3.py`** (UNTESTED)
  - Consumes from Kafka
  - Writes raw data to S3 bronze layer
  - ❌ No tests, needs refactoring

- **`flink_flight_consumer.py`** (ALTERNATIVE)
  - Another consumer using Flink (not used currently)
  - Historical artifact? Can be deleted?

#### Purpose of this folder:
> "Connect to external data source and feed into our streaming pipeline"

---

### **2. `Flink/` - Real-time Processing (Target Architecture)** 🎯
**Purpose**: Production-grade stream processing replacing Faust
**Status**: Planned (not yet implemented)
**Why Flink?**: See ENTERPRISE_READINESS_ASSESSMENT.md Section 1.1

#### Planned Files:
- `flink_streaming_processor.py` (PyFlink) or `src/main/java/...` (Java/Scala)
  - Kafka source → Windowing aggregations → S3/Snowflake sink
  - Stateful processing with RocksDB backend
  - Checkpointing to S3 for fault tolerance
- `conf/flink-conf.yaml` - Flink cluster configuration
- `lib/custom_connectors/` - Custom sink/source connectors
- `monitoring/` - Flink metrics reporters (Prometheus)

#### Planned Structure:
```
Flink/
├── src/
│   ├── main/java/com/flight/           # Java/Scala implementation
│   │   ├── FlinkStreamProcessor.java
│   │   ├── WindowOperator.java
│   │   └── FlinkCEPAlerts.java
│   └── main/python/                    # PyFlink alternative
│       └── flink_streaming_processor.py
├── conf/
│   ├── flink-conf.yaml                 # JobManager/TaskManager config
│   └── log4j.properties                # Logging configuration
├── lib/                                # Custom libraries
│   ├── flink-snowflake-connector.jar
│   └── custom-udfs/
└── monitoring/
    └── metrics_reporter.py             # Prometheus exporter
```

---

### **3. `Spark/` - Batch Processing (Target Architecture)** 🎯
**Purpose**: Distributed batch analytics replacing Pandas
**Status**: Planned (not yet implemented)
**Why Spark?**: Scalable ML, TB-scale data, fault tolerance

#### Planned Files:
- `spark_batch_processor.py` (PySpark)
  - Read from S3 silver layer (Parquet)
  - Daily/hourly aggregations, ML feature engineering
  - Write to Snowflake Gold layer
- `transformations/`
  - `aggregations.py` - GROUP BY, window functions
  - `enrichments.py` - Add derived columns (route, airline)
  - `ml_features.py` - Feature extraction for ML models
- `utils/`
  - `spark_utils.py` - SparkSession factory, config
  - `s3_utils.py` - S3 access optimizations (S3A, partitioning)
- `config.json` - Spark-specific configuration (warehouse size, etc.)

#### Planned Structure:
```
Spark/
├── spark_batch_processor.py            # Main ETL job
├── spark_streaming_processor.py        # Optional: Structured Streaming
├── transformations/
│   ├── aggregations.py                #.groupBy().agg()
│   ├── enrichments.py                 # Derived columns
│   └── ml_features.py                 # Feature engineering
├── utils/
│   ├── spark_utils.py                 # SparkSession builder
│   └── s3_utils.py                    # S3 read/write optimizations
├── config.json                        # Spark configuration
└── tests/
    ├── test_spark_batch.py            # Unit tests with local SparkSession
    └── fixtures/
        └── sample_flights_10k.parquet
```

---

### **4. `Faust/` - Stream Processing (Legacy)**
**Purpose**: Transform raw data through layers (Bronze → Silver → Gold)
**Status**: Active but to be **migrated to Flink** (see Roadmap)
**Legacy Note**: This is the current implementation. Plan to replace with Flink.

**Purpose**: Transform raw data through layers (Bronze → Silver → Gold)

#### Files:

**Core Transformations:**
- **`transformation_utils.py`** (NEW)
  - Pure functions for data transformations
  - `filter_valid_flights()` - filter records with coordinates
  - `transform_flight_data()` - convert to DataFrame
  - `parse_s3_key_timestamp()` - extract timestamps from file paths
  - `generate_silver_key()` - create partitioned S3 keys
  - ✅ **Well-tested** (18 tests, 100% coverage)
  - ⭐ **Excellent** - no AWS dependencies, pure logic

- **`bronze_to_silver.py`** (REFACTORED)
  - Reads raw JSON from S3 bronze layer
  - Validates with Pydantic schemas
  - Transforms and writes to S3 silver layer (partitioned by date/hour)
  - Now uses `BronzeToSilverTransformer` class (testable)
  - ✅ **Well-tested** (16 tests, ~90% coverage)
  - ⭐ **Good example** of dependency injection

- **`silver_to_gold.py`** (NEEDS REFACTORING)
  - Reads from silver layer
  - Aggregates/rolls up data
  - Writes to gold layer (aggregated tables)
  - ❌ **No tests**, uses global S3 client
  - 🔧 **Needs**: Refactor to class, add tests

- **`faust_app.py`**
  - Faust streaming application definition
  - Defines agents, tables, streams
  - Connects Kafka topics to processing functions
  - ⚠️ Complex, integration-level testing needed

- **`analytics_dashboard.py`**
  - Reads from Snowflake gold layer
  - Prints analytics to console
  - Shows: daily summaries, top countries, altitude stats
  - Used for manual inspection
  - ❌ No tests, simple script

#### Purpose of this folder:
> "Take raw data and make it useful through progressive transformations"

---

### **5. `schemas/` - Data Validation**
**Purpose**: Define and enforce data quality rules

#### Files:
- **`flight_schema.py`** (NEW)
  - `FlightRecord` Pydantic model
  - Validates: icao24 format, coordinate ranges, timestamp reasonableness
  - Field validators: strip callsign, normalize data
  - `FlightBatch` for collections
  - ✅ **Well-tested** (19 tests, 96% coverage)
  - ⭐ **Critical** for catching bad data early

#### Purpose of this folder:
> "Ensure only valid data flows through our pipeline"

---

### **6. `dagster_app/` - Orchestration**
**Purpose**: Alternative orchestration using Dagster framework

#### Files:
- **`defs.py`** - Dagster definitions entry point
- **`assets/ingestion.py`** - Bronze asset definition
- **`assets/silver.py`** - Silver asset definition
- **`assets/gold.py`** - Gold asset definition
- **`resources/s3_resource.py`** - S3 resource config
- **`resources/snowflake_resource.py`** - Snowflake resource config
- **`constants.py`** - Constants (bucket names, prefixes)
- ❌ **Dagster not fully integrated** - seems like experimental

#### Purpose:
> "Dagster provides data asset monitoring, scheduling, and observability"

---

### **7. `tests/` - Test Suite**
**Purpose**: Ensure code quality and prevent regressions

#### Structure:
```
tests/
├── test_defs.py              # Dagster definitions test (1 test)
└── unit/
    ├── test_flight_producer.py    # 8 tests
    ├── test_flight_schema.py      # 19 tests
    ├── test_transformation_utils.py  # 18 tests
    └── test_bronze_to_silver.py   # 16 tests
```

**Total: 62 passing tests** ✅

#### Purpose:
> "Automated quality assurance - every change must pass tests"

---

### **8. Core Orchestration Files** (Root directory)

#### Main Entry Points:

1. **`flight_streaming_orchestrator.py`** (MAIN - 587 lines)
   - The **brain** of the system
   - Manages: Docker services, dependencies, component lifecycle
   - Starts: Kafka, Zookeeper, producer, Faust workers
   - Interactive CLI (status, restart, logs, exit)
   - Checks: Health of all components
   - ✅ **Refactored**: Fixed bare except, unused imports
   - ⚠️ Needs: More tests, better error handling

2. **`start_flight_streaming.py`** (102 lines)
   - Simple launcher script
   - Checks: venv, .env, dependencies
   - Starts: Docker, then orchestrator
   - Quick start for beginners

3. **`streaming_config.py`** (158 lines)
   - **Centralized configuration**
   - AWS, Kafka, Snowflake, OpenSky settings
   - Geographic bounds, intervals, batch sizes
   - Validation: `config.validate()` checks all required vars
   - ⭐ **Good pattern** - single source of truth

4. **`run_complete_pipeline.py`**
   - Manual trigger for full ETL
   - Runs: bronze→silver, silver→gold transformations
   - Simple sequential execution

5. **`quick_status_check.py`**
   - Quick health check script
   - Checks: Docker, processes, S3 data
   - Simple yes/no status

---

### **9. Configuration Files**

| File | Purpose |
|------|---------|
| **`pyproject.toml`** | Project metadata, tool configs (ruff, pytest) |
| **`requirements.txt`** | Production dependencies (Kafka, boto3, pandas, etc.) |
| **`requirements-dev.txt`** | Dev dependencies (pytest, mypy, ruff, bandit) |
| **`.pre-commit-config.yaml`** | Pre-commit hooks (lint, type-check) |
| **`docker-compose.yml`** | Local Kafka + Zookeeper setup |
| **`Makefile`** | Standardized commands (Linux/Mac only) |
| **`.env`** | **Secrets** (AWS keys, Snowflake creds) - NOT in git |

---

### **10. Documentation Files**

| File | Purpose |
|------|---------|
| **`README.md`** | Original README (basic setup) |
| **`UNIFIED_SYSTEM_README.md`** | Detailed system documentation |
| **`ENTERPRISE_READINESS_ASSESSMENT.md`** | **Comprehensive audit** (what we did) |
| **`PROJECT_TRACKER.md`** | Current metrics, progress tracking |

---

## 🔄 **Data Flow Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                       OpenSky API                           │
│              (https://opensky-network.org)                 │
└─────────────────────────────┬───────────────────────────────┘
                              │ fetches every 10s
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              OpenSky/flight_producer.py                    │
│  • Fetches flights over India                             │
│  • Validates with Pydantic schemas                        │
│  • Sends to Kafka topic: realtime-flights                 │
└─────────────────────────────┬───────────────────────────────┘
                              │ streams
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Apache Kafka                             │
│              Topic: realtime-flights                       │
└─────────────────────────────┬───────────────────────────────┘
                              │ consumed
                              ▼
┌─────────────────────────────────────────────────────────────┐
│          OpenSky/flight_kafka_consumer_to_s3.py            │
│  • Reads from Kafka                                       │
│  • Writes raw JSON to S3 bronze/                          │
└─────────────────────────────┬───────────────────────────────┘
                              │ batch processing
                              ▼
┌─────────────────────────────────────────────────────────────┐
│          Faust/bronze_to_silver.py                         │
│  • Lists bronze files from S3                             │
│  • Filters valid flights (coords)                         │
│  • Validates with Pydantic                                │
│  • Writes to silver_flights/ (partitioned: YYYY/MM/DD/HH) │
└─────────────────────────────┬───────────────────────────────┘
                              │ batch processing
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           Faust/silver_to_gold.py                          │
│  • Reads from silver layer                                │
│  • Aggregations, enrichments                             │
│  • Writes to gold layer (aggregated tables)               │
└─────────────────────────────┬───────────────────────────────┘
                              │ batch load
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Snowflake                                 │
│         Table: flights_raw, flights_agg, top_airlines     │
└─────────────────────────────┬───────────────────────────────┘
                              │ queries
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           Faust/analytics_dashboard.py                     │
│  • Connects to Snowflake                                 │
│  • Runs analytical queries                               │
│  • Prints insights to console                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 **Key Files to Understand First**

### **For Interview Prep (Read These):**

1. **`ENTERPRISE_READINESS_ASSESSMENT.md`**
   - Shows what you've built and why
   - Lists remaining gaps
   - Interview talking points

2. **`OpenSky/flight_producer.py`**
   - Clean, testable code
   - Shows separation of concerns
   - Good error handling patterns

3. **`tests/unit/test_flight_producer.py`**
   - Example of good unit tests
   - Mocking external APIs
   - Edge case coverage

4. **`Faust/transformation_utils.py`**
   - **Pure functions** - easiest to understand
   - No external dependencies
   - Clear input→output mapping

5. **`schemas/flight_schema.py`**
   - Data validation concepts
   - Pydantic usage
   - Business rules as code

6. **`flight_streaming_orchestrator.py`**
   - Main orchestration logic
   - Shows how components work together
   - Health checking patterns

---

## ❌ **What Can Be Deleted/Archived?**

### **Safe to Delete:**
- `Faust/temp.py` - Temporary file
- `GOLD_LAYER_SETUP.md` - Superseded by other docs
- `ruff_issues.txt` - Auto-generated lint report (old)
- `consumer_to_file.py` - Unused consumer variant
- `fix_cert_issue.py` - Ad-hoc debugging script
- `one.py` - Test file
- `quick_status_check.py` - Replaced by better scripts?
- `start_flight_streaming.bat` - Windows batch (have .py version)
- `SYSTEM_STATUS.md` - Redundant with PROJECT_TRACKER.md

### **Keep (Important):**
- All code in `OpenSky/`, `Faust/`, `schemas/`
- All tests in `tests/`
- `dagster_app/` (maybe future use)
- `docker-compose.yml` (for local dev)
- Core orchestrators
- Documentation files

---

## 📊 **Current Test Coverage**

| Module | Tests | Status | Notes |
|--------|-------|--------|-------|
| `flight_producer.py` | 8 | ✅ 97% | Excellent |
| `flight_schema.py` | 19 | ✅ 96% | Excellent |
| `transformation_utils.py` | 18 | ✅ 100% | Perfect |
| `bronze_to_silver.py` | 16 | ✅ ~90% | Good |
| **Total** | **62** | ✅ | **~60% overall** |

---

## 🔍 **How to Navigate the Codebase**

### **If you want to understand...**

**"How does data flow?"** → Start with:
1. `OpenSky/flight_producer.py` (data source)
2. `Faust/bronze_to_silver.py` (first transformation)
3. `PROJECT_TRACKER.md` (architecture diagram)

**"How are tests structured?"** → Start with:
1. `tests/unit/test_flight_producer.py` (simple)
2. `tests/unit/test_transformation_utils.py` (pure functions)
3. `tests/unit/test_bronze_to_silver.py` (complex mocking)

**"How is configuration managed?"** → Start with:
1. `streaming_config.py` (central config)
2. `.env` (secrets)
3. `pyproject.toml` (tool configs)

**"How does the orchestrator work?"** → Start with:
1. `flight_streaming_orchestrator.py` (main class)
2. `start_flight_streaming.py` (entry point)
3. `check_system_status.py` (health checks)

---

## 🎯 **Recommended Learning Path (2 Hours)**

### **Hour 1: Core Concepts**
1. `ENTERPRISE_READINESS_ASSESSMENT.md` (skim, 20 min)
2. `OpenSky/flight_producer.py` (read carefully, 20 min)
3. `tests/unit/test_flight_producer.py` (see how it's tested, 15 min)
4. `Faust/transformation_utils.py` (pure functions, 15 min)
5. `schemas/flight_schema.py` (validation, 10 min)

### **Hour 2: Architecture**
1. `PROJECT_TRACKER.md` (current state, 15 min)
2. `flight_streaming_orchestrator.py` (orchestration, 25 min)
3. `Faust/bronze_to_silver.py` (refactored class, 20 min)
4. `.github/workflows/ci.yml` (CI/CD, 15 min)
5. `README.md` or `UNIFIED_SYSTEM_README.md` (overview, 5 min)

---

## 🚨 **Known Issues / Tech Debt**

| File | Issue | Priority |
|------|-------|----------|
| `silver_to_gold.py` | No tests, global S3 client | High |
| `flight_kafka_consumer_to_s3.py` | No tests, untested | High |
| `faust_app.py` | Complex, needs integration tests | Medium |
| `analytics_dashboard.py` | Simple script, no tests | Low |
| `check_system_status.py` | Redundant with monitoring | Low |
| `dagster_app/` | Not integrated, confusing | Low |
| `consumer.py` | What does this do? | Unknown |

---

## 💡 **Quick Start to Understanding**

**Step 1**: Run the tests and see them pass
```bash
pytest tests/unit/ -v
```

**Step 2**: Read a simple production file + its tests side-by-side
- Open `OpenSky/flight_producer.py` (left)
- Open `tests/unit/test_flight_producer.py` (right)
- See how tests exercise the code

**Step 3**: Trace one data point through the system
```
1. Producer creates: {"icao24": "801642", "latitude": 28.2, ...}
2. Schema validates it
3. Sends to Kafka
4. Consumer writes to S3 bronze/
5. Bronze→Silver transforms it
6. Checks validated fields
7. Writes to S3 silver/ with partition
```

**Step 4**: Ask specific questions
- "How does Kafka integration work?"
- "What's the difference between bronze and silver?"
- "How do we handle errors?"
- "What's Pydantic used for?"

---

## 📝 **Questions to Answer While Reading**

For each file, ask:
1. **What is its purpose?** (1 sentence)
2. **What are its main functions/classes?**
3. **What external dependencies does it have?** (Kafka, S3, Snowflake)
4. **How is it tested (or not)?**
5. **How does it connect to other files?**

---

**Start reading now**: Open `ENTERPRISE_READINESS_ASSESSMENT.md` first - it gives you the strategic overview. Then come back here to understand the tactical details.

**What specific component would you like to understand first?** I can deep-dive into any file or concept!
