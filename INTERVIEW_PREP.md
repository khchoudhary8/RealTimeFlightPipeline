# 🎓 Data Engineering Interview Masterclass: The Flight Data Platform

This guide turns your project into a **Senior Data Engineer** level narrative. It anticipates the tough "Why?" questions and gives you the architectural reasoning to crush the interview.

---

## 🚀 The 60-Second Pitch (Start here)
> *"I built an end-to-end real-time flight tracking platform that processes live data from the OpenSky Network. 
> To ensure scalability and fault tolerance, I decoupled ingestion from processing using **Kafka**. 
> I used **Faust** for stream processing to land raw data into an **S3 Data Lake** (Bronze Layer). 
> For the batch layer, I used **Dagster** to orchestrate a Medallion Architecture, transforming raw JSON into optimized **Parquet** (Silver) and finally into **Snowflake** (Gold) for analytics. 
> This separation allows the system to handle API spikes without data loss and provides a replayable history of all flight events."*

---

## 🔥 Deep Dive: "Why not just a Python Script?"

**Interviewer**: *"You over-engineered this. Why Kafka? Why S3? A script + Postgres is enough."*

**Your Answer**: *"A script works for a prototype, but it fails the **Day 2 Operations** test."*

### 1. Decoupling & Backpressure (Kafka)
*   **Scenario**: The OpenSky API suddenly sends 50,000 flights in one second (a spike).
*   **Script Approach**: The script tries to write 50k rows to Postgres. Postgres locks up. The script crashes. Data is lost.
*   **My Architecture**: The Producer pushes 50k events to **Kafka**. Kafka absorbs them instantly (it can handle millions/sec). The **Consumer** (Worker) reads them at its own pace (e.g., 1000/sec). The system effectively **buffers** the spike. No crash. No data loss.

### 2. The "History" Problem (S3 Data Lake)
*   **Scenario**: A bug in my parsing logic (Silver Layer) was calculating `velocity` incorrectly for 2 months. 
*   **Script Approach**: I only stored the final processed data in the DB. The original raw JSON is gone. I cannot fix the historical data.
*   **My Architecture**: I stored the **Raw JSON** in S3 (Bronze). I fix the bug in the Silver Asset, delete the bad Silver data, and **Replay** the pipeline from S3. The history is corrected. S3 provides **Time Travel** for my code logic.

### 3. Compute/Storage Separation (Snowflake)
*   **Scenario**: The CEO wants a complex year-end report involving billions of rows.
*   **Script Approach**: Running this query on the same Postgres instance used for ingestion slows down the write speed. The ingestion script times out.
*   **My Architecture**: Snowflake separates Storage (S3) from Compute. I spin up a **Large Warehouse** for the report. The ingestion (using a separate Small Warehouse) is completely unaffected.

---

## 🛠️ Technology Choices & Alternatives

### Ingestion: Kafka vs. Others
| Technology | Why Use It? | Why I Chose Kafka? |
| :--- | :--- | :--- |
| **RabbitMQ** | Good for complex routing/task queues. | Kafka is better for **Log Aggregation** and huge throughput. I needed replayability (Redonable Log). |
| **AWS Kinesis** | Managed, less ops. | **Vendor Lock-in**. Kafka is open-source standard. (Though in Prod I'd use MSK/Confluent). |
| **Rest API** | Simple. | Synchronous. If the receiver is down, the sender waits/fails. Kafka is Asynchronous. |

### Processing: Faust vs. Spark vs. Flink
| Technology | Why Use It? | Why I Chose Faust? |
| :--- | :--- | :--- |
| **Spark Streaming** | Huge scale (TB/hour), micro-batches. | resource heavy (JVM). Overkill for this volume. |
| **Flink** | True low-latency streaming. Complex. | High ops overhead. |
| **Faust** | **Python Native!** | I'm a Python engineer. It's lightweight, uses the same language as my producers, and good enough for 10k msg/sec. |

### Orchestration: Dagster vs. Airflow
| Technology | Why Use It? | Why I Chose Dagster? |
| :--- | :--- | :--- |
| **Airflow** | Industry standard, task-based. | It schedules "Tasks" (Python scripts), not "Data". You don't know *what* data was produced. |
| **Dagster** | **Asset-based**. | It knows about the **Data Assets** (Tables/Files). It provides lineage out-of-the-box. It makes **testing** easier (resources/IO managers). |

### Storage Format: JSON vs. Parquet vs. Delta
- **JSON**: Human readable, easy to debug (Good for Bronze).
- **Parquet**: Columnar format. 10x faster for analytics (aggregations/reads) and highly compressed (Good for Silver).
- **Delta Lake/Iceberg**: Adds ACID transactions to S3. I used this for Silver to ensure readers don't see half-written files.

---

## 🧠 Advanced Follow-Up Questions

### Q1: "How would you handle duplicates?"
**Answer**: 
1.  **Ingestion:** Kafka guarantees "At Least Once" delivery (mostly). So duplicates can happen.
2.  **Silver Layer:** In my Dagster asset (`silver.py`), I perform deduplication using `.unique(subset=['icao24', 'time_position'])` before writing to Parquet.
3.  **Gold Layer:** I use `MERGE` statements (or `write_pandas` with overwrite mode for snapshots) to ensure idempotency. Running the job twice doesn't double the data.

### Q2: "What if the OpenSky API schema changes?"
**Answer**:
This is "Schema Drift".
1.  **Bronze (S3)** is aggressive. It saves *whatever* JSON it gets. It never fails on schema change.
2.  **Silver (Dagster)** would likely fail if a key column is missing. I would use **Dagster Sensors** or **Great Expectations** checks to validate the schema before processing. If it fails, I get a PagerDuty alert, update the code, and **Replay** the failed events from Bronze.

### Q3: "How do you scale to 100x traffic?" (Scaling & Accessibility)
**Answer**:
1.  **Kafka Middleware**: Increase **Partitions** (e.g., from 1 to 50). This allows parallel processing.
2.  **Processing**: Deploy Faust via **Kubernetes Deployment**. Because workers share the same consumer group, they automatically rebalance the 50 partitions among themselves. I'd configure a Horizontal Pod Autoscaler (HPA) to add workers based on CPU load.
3.  **Database**: Snowflake handles infinite storage scaling automatically. For query accessibility (concurrent analysts), I would configure **Multi-Cluster Warehouses** to automatically spin up additional compute nodes when query queuing occurs.

### Q4: "How is your architecture Fault Tolerant and Highly Available?"
**Answer**: 
*   **Decoupling is key**: If the Snowflake data warehouse goes down, the OpenSky ingester (Producer) doesn't care. It keeps fetching and pushing to Kafka. If Faust goes down, Kafka retains the messages (Fault Tolerance). Once services return, they pick up exactly where they left off (using Consumer Group offsets). 
*   **High Availability**: In an enterprise deployment, Kafka would be deployed via AWS MSK across 3 Availability Zones (AZs) with a replication factor of 3. Kubernetes worker nodes would also spread across AZs.

### Q5: "How do you handle overnight or weekend failures where no one is watching?"
**Answer**:
*   **Orchestration Auto-retries**: In Dagster, I configure `RetryPolicy(max_retries=3, delay=300)`. Transient network issues or Snowflake API timeouts resolve themselves automatically.
*   **Alerting**: I configure **Prometheus** to monitor Kafka Consumer Lag. If lag exceeds 10 minutes (meaning the Faust worker died silently), an alert fires to Slack/PagerDuty.
*   **Dead Letter Queues (DLQ)**: If a specific malformed flight record continuously crashes the pipeline, Kafka/Faust routes it to a DLQ so the pipeline skips it and continues processing the rest until morning.

### Q6: "How do you solve Out of Memory (OOM) issues if data size explodes suddenly?"
**Answer**:
*   **Streaming limits**: Faust processes events lazily (one-by-one or in small chunks of 1,000 via a windowing `buffer`). It only keeps the current batch in memory before flushing to S3.
*   **Batching limits**: In Dagster, using `polars` helps because it's highly memory efficient. If data exceeds RAM, I would configure polars to use streaming execution `.collect(streaming=True)`. Alternatively, for massive scale, I would switch the Silver transformation to **Apache Spark**, which spills to disk securely to avoid OOM crashes.

### Q7: "What happens if a job is taking too long?"
**Answer**:
*   **Dagster Timeouts**: I enforce an execution timeout at the Dagster Job level. If the `etl_pipeline` takes more than 45 minutes when it normally takes 5, it gets killed, and an alert is sent.
*   **Performance Profiling**: I would look at the Dagster UI's Gantt charts to identify the exact step. Usually, it's either an unoptimized SQL join in the Gold layer (fixed via a clustering key in Snowflake) or a slow file read (fixed by partitioning the Silver Parquet files better).

---

## 🎯 Behavioral Strategy: "The Bug Story"
*Prepare this story. Interviewers love it.*

> "During the project, I noticed my **Gold Layer** timestamps were failing in Snowflake. 
> **The Problem**: Polars was inferring High-Precision Nanosecond timestamps, which Snowflake rejected.
> **The Debug**: I wrote a dedicated script `verify_snowflake_data.py` to inspect the raw types in the DB.
> **The Fix**: I implemented robust type coercion in the Gold asset, forcing seconds-precision.
> **The Lesson**: Always validate data types at the boundaries between systems (Python -> SQL)."
