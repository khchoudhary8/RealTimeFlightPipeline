# 🔄 Lambda Architecture: Flink + Spark

**Deep dive into our hybrid real-time + batch processing system**

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Why Lambda Architecture?](#why-lambda-architecture)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [Technology Choices](#technology-choices)
5. [Data Flow](#data-flow)
6. [Configuration](#configuration)
7. [Implementation Guide](#implementation-guide)
8. [Alternatives Considered](#alternatives-considered)
9. [Best Practices](#best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Further Reading](#further-reading)

---

## Overview

**Lambda Architecture** is a data processing paradigm introduced by Nathan Marz that combines **real-time** and **batch** processing to balance **low latency**, **fault tolerance**, and **data completeness**.

### Core Principles

1. **Immutability**: All data is immutable; never update in place, only append
2. **Recomputation**: Batch layer can recompute any view from raw data
3. **Separation of concerns**: Speed layer for low-latency, batch layer for accuracy
4. **Unified serving**: Both layers serve from the same storage (Snowflake)

### The Three Layers

```
                ┌─────────────────────┐
                │   Data Sources      │
                │  (OpenSky API)     │
                └─────────┬───────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Speed Layer (Flink)                       │
│  • Low-latency processing (sub-second)                     │
│  • Incremental aggregations (5-min, 1-hour windows)        │
│  • Stateful operators with exactly-once guarantees          │
│  • Writes to real-time views (last 24h)                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          └───────────────┬──────────────────┘
                                          │
┌─────────────────────────────────────────────────────────────┐
│                  Serving Layer (Snowflake)                  │
│  • FLIGHTS_STREAMING: Real-time data from Flink            │
│  • FLIGHTS_BATCH: Historical aggregates from Spark         │
│  • FLIGHTS_COMPLETE: UNION view for "full picture"         │
└─────────────────────────────────────────────────────────────┘
                          ▲
                          │
┌─────────────────────────────────────────────────────────────┐
│                    Batch Layer (Spark)                       │
│  • Scalable distributed processing (TB-scale)              │
│  • Comprehensive aggregations (daily, monthly, yearly)    │
│  • Machine learning (feature engineering, model training) │
│  • Can recompute entire history (correctness guarantee)    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │   Raw Storage       │
                │  (S3 Bronze)        │
                └─────────────────────┘
```

---

## Why Lambda Architecture?

### The Problem

We need to support two different types of queries:

1. **Real-time**: "Where is flight AI882 right now?" → Needs sub-second response, recent data only
2. **Historical**: "What were the busiest routes last month?" → Needs full dataset, can tolerate seconds/minutes

### Single-System Limitations

| System | Real-time? | Historical? | Cost (at scale) |
|--------|------------|-------------|-----------------|
| **Kafka + Faust only** | ✅ Yes | ❌ No (replay expensive) | High (stream everything) |
| **Spark Structured Streaming** | ⚠️ Possible | ✅ Yes | Medium-High |
| **Flink only (Kappa)** | ✅ Yes | ⚠️ Possible (replay) | Medium (but replay costs) |
| **Lambda (Flink+Spark)** | ✅ Yes | ✅ Yes | **Low** (batch cheaper) |

### Why Not Kappa?

Kappa architecture uses a single streaming system for all processing. It's simpler but:

- ❌ **Replaying 1 year of history through Flink** is expensive (compute + time)
- ❌ **Complex aggregations** (multi-table joins, window functions) perform better in batch
- ❌ **Machine learning** needs distributed training (Spark MLlib)
- ✅ **Simpler ops** (only one system to maintain)
- ✅ **Good for** < 30 days of data, no heavy batch needs

**Our choice: Lambda** because:
- We want to keep **years of flight data**
- Daily/Hourly batch aggregations are **cost-effective** in Spark
- Real-time dashboard needs **sub-second latency**
- We can **scale independently**: more Flink for throughput, more Spark for compute

---

## Architecture Deep Dive

### 1. Speed Layer (Apache Flink)

**Purpose**: Process live Kafka stream with minimal latency.

#### Key Concepts

- **Event Time vs Processing Time**: Use event timestamps from `time_position` for windowing
- **Watermarks**: Handle out-of-order events (flights might report delayed)
- **State**: Store flight position history, track geofence violations
- **Checkpoints**: Exactly-once via two-phase commit to S3/Snowflake (every 60s)

#### Typical Flink Job Structure

```java
// Java example
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
env.enableCheckpointing(60000); // 60s checkpoint interval

// Source: Kafka
FlinkKafkaConsumer<String> consumer = new FlinkKafkaConsumer<>(
    "realtime-flights",
    new SimpleStringSchema(),
    properties
);
DataStream<String> raw = env.addSource(consumer);

// Parse JSON
DataStream<Flight> flights = raw
    .map(new MapFunction<String, Flight>() {
        public Flight map(String value) {
            ObjectMapper mapper = new ObjectMapper();
            return mapper.readValue(value, Flight.class);
        }
    });

// Assign timestamps and watermarks
DataStream<Flight> withTimestamps = flights.assignTimestampsAndWatermarks(
    WatermarkStrategy
        .<Flight>forBoundedOutOfOrderness(Duration.ofSeconds(5))
        .withTimestampAssigner((event, timestamp) -> event.time_position * 1000L)
);

// 5-minute tumbling window aggregations
DataStream<WindowedAgg> fiveMinAggs = withTimestamps
    .windowAll(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new FlightAggregator().

    );

// Stateful processing: Track aircraft in restricted zones
KeyedStream<Flight, String> byIcao = withTimestamps.keyBy(Flight::getIcao24);
DataStream<Alert> alerts = byIcao
    .connect(geofenceStream)
    .process(new GeofenceDetector())
    .name("geofence-monitor");

// Sinks
fiveMinAggs.addSink(new FlinkSnowflakeSink()); // Real-time view
alerts.addSink(new AlertKafkaTopic()); // For downstream consumers
```

#### Flink Configuration

```yaml
# flink-conf.yaml
jobmanager.memory.process.size: 4096m
taskmanager.memory.process.size: 8192m
parallelism.default: 10
state.backend: rocksdb
state.backend.incremental: true
state.checkpoints.dir: s3://bucket/flink-checkpoints/
state.savepoints.dir: s3://bucket/flink-savepoints/
execution.checkpointing.interval: 60000
high-availability: zookeeper
```

#### Exactly-Once Guarantees

- Enable **checkpointing** (every 60s)
- Use **two-phase commit sink** (e.g., Flink's `TwoPhaseCommitSink` for Snowflake)
- Kafka source runs in **exactly-once mode** (`isolation.level=read_committed`)

### 2. Batch Layer (Apache Spark)

**Purpose**: Process all historical data at scale.

#### Key Concepts

- **Data Locality**: Read from S3 with optimal partitioning (use `spark.sql.files.maxPartitionBytes`)
- **Catalyst Optimizer**: Let Spark optimize query plans (avoid UDFs when possible)
- **Shuffle Management**: Tune `spark.sql.shuffle.partitions` (default 200, adjust based on data)
- **Dynamic Allocation**: Enable for cost optimization (scale executors based on workload)

#### Typical Spark Job

```python
# spark_batch_processor.py
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import *

# Create SparkSession with S3 access
spark = SparkSession.builder \
    .appName("FlightBatchProcessor") \
    .config("spark.hadoop.fs.s3a.endpoint", "s3.amazonaws.com") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
    .getOrCreate()

# Read from S3 (partitioned by year=YYYY/month=MM/day=DD/hour=HH)
df = spark.read \
    .option("basePath", f"s3://{BUCKET}/silver_flights/") \
    .parquet(f"s3://{BUCKET}/silver_flights/*/*/*/*/*.parquet") \
    .withColumn("flight_date", F.to_date("time_position"))

# Daily aggregations by country
daily_stats = df.groupBy(
    "flight_date", "origin_country"
).agg(
    F.count("*").alias("flight_count"),
    F.avg("baro_altitude").alias("avg_altitude"),
    F.stddev("velocity").alias("std_velocity"),
    F.min("time_position").alias("first_seen"),
    F.max("time_position").alias("last_seen")
).orderBy(F.desc("flight_date"), F.desc("flight_count"))

# Top routes (requires origin/destination - would need stateful assignment)
# In real scenario, you'd track consecutive positions to infer route

# Write to Snowflake
sfOptions = {
    "sfURL": SNOWFLAKE_ACCOUNT,
    "sfUser": SNOWFLAKE_USER,
    "sfPassword": SNOWFLAKE_PASSWORD,
    "sfDatabase": "FLIGHT_ANALYTICS",
    "sfSchema": "PUBLIC",
    "sfWarehouse": "COMPUTE_WH"
}

# Overwrite partition (assuming partitioned table)
daily_stats.write \
    .format("snowflake") \
    .options(**sfOptions) \
    .option("dbtable", "FLIGHTS_DAILY_AGG") \
    .mode("overwrite") \
    .save()
```

#### Spark Configuration

```properties
# spark-defaults.conf
spark.master                    local[*]
spark.app.name                  FlightBatchProcessor
spark.driver.memory             4g
spark.executor.memory           8g
spark.dynamicAllocation.enabled true
spark.dynamicAllocation.minExecutors 2
spark.dynamicAllocation.maxExecutors 20
spark.sql.adaptive.enabled      true
spark.sql.parquet.compressionCodec snappy
spark.sql.files.maxPartitionBytes 256m
spark.sql.shuffle.partitions    200
spark.sql.autoBroadcastJoinThreshold -1  # Disable broadcast for large joins
spark.sql.legacy.timeParserPolicy LEGACY  # For timestamp parsing
```

### 3. Serving Layer (Snowflake)

**Purpose**: Merge real-time and batch data into unified views.

#### Table Structure

```sql
-- Raw flight data (loaded by batch layer)
CREATE OR REPLACE TABLE flights_raw (
    icao24 VARCHAR(20),
    callsign VARCHAR(20),
    origin_country VARCHAR(50),
    time_position TIMESTAMP,
    longitude FLOAT,
    latitude FLOAT,
    baro_altitude FLOAT,
    velocity FLOAT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    partition_date DATE AS (DATE(time_position))
) CLUSTER BY (partition_date, origin_country);

-- Real-time view (updated by Flink via streaming inserts)
CREATE OR REPLACE VIEW flights_streaming AS
SELECT * FROM flights_raw
WHERE processed_at >= DATEADD(hour, -24, CURRENT_TIMESTAMP());

-- Batch aggregates (updated by Spark daily)
CREATE OR REPLACE TABLE flights_daily_agg (
    flight_date DATE,
    origin_country VARCHAR(50),
    flight_count BIGINT,
    avg_altitude FLOAT,
    std_velocity FLOAT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Unified view (combines both)
CREATE OR REPLACE VIEW flights_complete AS
-- Recent flights (high detail, last 24h)
SELECT 'STREAMING' as data_source, * FROM flights_streaming
UNION ALL
-- Older flights (aggregated, older than 24h)
SELECT 'BATCH' as data_source, * FROM flights_daily_agg
WHERE flight_date < DATEADD(day, -1, CURRENT_DATE());
```

---

## Data Flow

### End-to-End Journey

1. **Ingestion**: OpenSky API → Kafka (every 10s)
2. **Bronze**: Kafka consumer writes raw JSON to `s3://bucket/bronze/YYYY/MM/DD/HH/`
3. **Speed Path**: Flink reads Kafka → 5-min window → Snowflake real-time view (every 5 min)
4. **Batch Path**: Spark reads S3 silver → daily aggregates → Snowflake batch table (once daily at 2AM)
5. **Serving**: Snowflake UNION view provides seamless query experience

### Partitioning Strategy

```
S3 structure:
s3://bucket/
├── bronze/
│   └── year=YYYY/month=MM/day=DD/hour=HH/
│       └── flights_YYYYMMDDHHMMSS.json
├── silver/
│   └── year=YYYY/month=MM/day=DD/
│       └── flights_YYYYMMDD.parquet  (partitioned by date)
└── gold/  # optional, pre-computed aggregates
    └── daily_agg/year=YYYY/month=MM/
        └── flights_agg_YYYYMMDD.parquet
```

**Why partition by date?**
- Easy to expire old data (S3 lifecycle rules)
- Efficient querying (partition pruning in Spark/Snowflake)
- Simple incremental processing (process only new partitions)

---

## Configuration

The `streaming_config.py` module centralizes all configuration.

### Environment Variables

```bash
# AWS
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=AKIA...
S3_BUCKET_NAME=realtimeflightstreamingbucket

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=realtime-flights
KAFKA_GROUP_ID_FLINK=flink-speed-layer
KAFKA_GROUP_ID_SPARK=spark-batch-consumer

# Flink (optional via env, mostly flink-conf.yaml)
FLINK_CHECKPOINT_INTERVAL=60000
FLINK_PARALLELISM=10
FLINK_STATE_BACKEND=rocksdb
FLINK_STATE_CHECKPOINT_DIR=s3://bucket/flink-checkpoints/

# Spark
SPARK_APP_NAME=FlightBatchProcessor
SPARK_MASTER=local[*]
SPARK_EXECUTOR_MEMORY=8g
SPARK_DRIVER_MEMORY=4g
SPARK_DYNAMIC_ALLOCATION_ENABLED=true
SPARK_SHUFFLE_PARTITIONS=200

# Snowflake
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/rsa_key.p8
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=FLIGHT_ANALYTICS
SNOWFLAKE_SCHEMA=PUBLIC

# OpenSky
OPENSKY_API_URL=https://opensky-network.org/api/states/all
FETCH_INTERVAL_SECONDS=10
INDIA_BOUNDS=6.0,38.0,68.0,97.0
```

### Configuration Validation

Run `python streaming_config.py` to validate all required variables are set.

---

## Implementation Guide

### Prerequisites

- **Java 11+** for Flink
- **Python 3.8+** for Spark (PySpark)
- **Scala 2.12** (if using Scala Spark)
- **Docker** for Kafka/Zookeeper
- **AWS CLI** configured with S3 access
- **Snowflake account** with load access

### Step-by-Step Setup

#### 1. Flink Local Mode

```bash
# Download Flink (example version 1.17)
wget https://archive.apache.org/dist/flink/flink-1.17.0/flink-1.17.0-bin-scala_2.12.tgz
tar -xzf flink-1.17.0-bin-scala_2.12.tgz
cd flink-1.17.0

# Start Flink local cluster
./bin/start-cluster.sh

# Verify UI: http://localhost:8081

# Submit job
./bin/flink run \
  -c com.flight.FlinkStreamProcessor \
  -p 4 \  # parallelism
  -yD taskmanager.memory.process.size=8192m \
  -yD state.backend=rocksdb \
  -yD state.checkpoints.dir=s3://bucket/flink-checkpoints/ \
  ./target/flight-processor.jar

# Check job in UI
# Stop
./bin/cluster.sh
```

#### 2. Spark Local Mode

```bash
# Install PySpark
pip install pyspark

# Run job
spark-submit \
  --master local[*] \
  --conf spark.driver.memory=4g \
  --conf spark.executor.memory=8g \
  --conf spark.sql.parquet.compressionCodec=snappy \
  --packages net.snowflake:snowflake-jdbc:3.13.6,net.snowflake:spark-snowflake_2.12:2.9.0 \
  Spark/spark_batch_processor.py \
  --date 2024-01-15 \
  --bucket realtimeflightstreamingbucket
```

#### 3. Integration with Dagster

```python
# dagster_app/defs.py - add Flink asset
@asset
def flink_streaming_health(context) -> bool:
    """Check if Flink job is running and healthy."""
    response = requests.get("http://localhost:8081/jobs")
    jobs = response.json()["jobs"]
    running = [j for j in jobs if j["status"] == "RUNNING"]
    return len(running) > 0

@asset
def spark_batch_success(context) -> bool:
    """Check if last Spark job succeeded."""
    # Query Snowflake for latest batch timestamp
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(updated_at) FROM flights_daily_agg")
    last_update = cursor.fetchone()[0]
    # Check if it's today
    return last_update.date() == datetime.utcnow().date()
```

---

## Alternatives Considered

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **Faust-only** | Simple, Python-native | Not truly distributed, limited state | ❌ Rejected for production |
| **Spark Streaming** | Unified batch+stream, good ML | Higher latency (100ms+), more operational overhead | ⚠️ Considered, but Flink better for low-latency |
| **Kafka Streams** | Lightweight, exactly-once | JVM only, limited to Kafka ecosystem | ❌ Too Kafka-centric |
| **Kinesis + Lambda** | Serverless, AWS-native | Vendor lock-in, limited state size | ❌ Not for multi-cloud |
| **Flink only (Kappa)** | Simpler ops, one system | Replay costs, batch not as optimized | ⚠️ Good for <30 days data |

**Final decision**: **Lambda with Flink+Spark** gives us the best of both worlds with independent scaling.

---

## Best Practices

### Flink

- ✅ **Use event time** (from flight data) not processing time
- ✅ **Set appropriate watermark delay** (5-30s based on expected lateness)
- ✅ **Enable incremental checkpoints** (RocksDB) for large state
- ✅ **Monitor checkpoint duration** (should be < checkpoint interval)
- ✅ **Tune parallelism** to match Kafka partition count

### Spark

- ✅ **Use Parquet** (not JSON) for storage (10x smaller, faster queries)
- ✅ **Partition by date** for time-series data (improves pruning)
- ✅ **Avoid UDFs** when possible (use built-in functions for Catalyst optimization)
- ✅ **Enable dynamic allocation** for cost savings
- ✅ **Cache reused datasets** (`df.cache()`) but monitor memory

### Snowflake

- ✅ **Cluster by high-cardinality columns** (partition_date, origin_country)
- ✅ **Use materialized views** for frequently queried aggregates
- ✅ **Auto-suspend warehouses** after 5-10 minutes idle
- ✅ **Separate compute for batch vs real-time** (different warehouse sizes)

### Lambda Pattern

- ✅ **Keep raw data immutable** (never delete/modify bronze)
- ✅ **Layer recomputation** should be possible (re-run batch from any date)
- ✅ **Version your schemas** (use Confluent Schema Registry)
- ✅ **Monitor both layers separately** (Flink lag vs Spark duration)
- ✅ **Implement graceful degradation** (if Flink down, still serve batch)

---

## Common Pitfalls

### 1. **State Size Explosion** (Flink)

**Problem**: State grows unbounded, causing checkpoint failures.

**Solution**: Use **TTL** (time-to-live) on state, or periodic cleanup operators:
```java
StateTtlConfig ttlConfig = StateTtlConfig
    .newBuilder(Time.hours(24))
    .setStateVisibility(StateVisibility.NeverReturnExpired)
    .build();
stateDescriptor.enableTimeToLive(ttlConfig);
```

### 2. **Skewed Partitions** (Spark)

**Problem**: One partition huge (e.g., US flights dominate), causing stragglers.

**Solution**: **Salting** - add random prefix to partition key:
```python
df.withColumn("salt", F.rand(seed=42) * 10).groupBy("salt", "origin_country")...
```

### 3. **Small Files Problem** (S3)

**Problem**: Many tiny files from streaming hurts query performance.

**Solution**: 
- **Compact** small files periodically (Spark job that repartitions)
- Use **S3DistCp** or **EMRFS consistent view**
- Set `spark.sql.files.maxPartitionBytes` to control partition size

### 4. **Cross-layer Inconsistency**

**Problem**: Flink and Spark outputs don't match due to logic drift.

**Solution**: 
- **Share transformation code** (extract to common library)
- **Reconciliation job** daily: compare row counts, checksums
- **Golden dataset**: maintain small sample manually verified

### 5. **Kafka Consumer Lag**

**Problem**: Flink falls behind, lag grows > 10 minutes.

**Solution**:
- Increase **parallelism** (scale TaskManagers)
- Tune **checkpoint interval** (longer = less overhead but slower recovery)
- **Monitor lag** via Prometheus `kafka_consumer_lag_seconds`
- Consider **increasing partitions** (more parallelism)

---

## Further Reading

### Books
- [Streaming Systems by Tyler Akidau](https://www.oreilly.com/library/view/streaming-systems/9781491893961/)
- [Spark: The Definitive Guide by Matei Zaharia](https://www.oreilly.com/library/view/spark-the-definitive/9781491911434/)
- [Designing Data-Intensive Applications by Martin Kleppmann](https://dataintensive.net/)

### Documentation
- [Apache Flink Docs](https://flink.apache.org/docs/stable/)
- [Apache Spark SQL Guide](https://spark.apache.org/docs/latest/sql-programming-guide.html)
- [Snowflake Best Practices](https://docs.snowflake.com/en/user-guide/intro-key-concepts)

### Blog Posts
- [Lambda Architecture in Practice](https://eng.uber.com/introducing-marmaray/)
- [Flink Checkpointing Deep Dive](https://www.ververica.com/blog/flink-checkpointing-alignment)
- [Spark Performance Tuning](https://databricks.com/blog/2017/08/31/improving-spark-performance-with-shuffle-partitioning.html)

---

## 📞 Questions?

For questions about implementation, see:
- `README.md` - Quick start
- `ENTERPRISE_READINESS_ASSESSMENT.md` - Gap analysis
- `CODEBASE_GUIDE.md` - Codebase navigation

**Ready to implement?** Start with `Flink/` and `Spark/` directories!
