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

### Q3: "How do you scale to 100x traffic?"
**Answer**:
1.  **Kafka**: Increase **Partitions** (e.g., from 1 to 50).
2.  **Processing**: Increase **Faust Workers**. Because they share the same consumer group, they automatically rebalance the 50 partitions among themselves.
3.  **S3**: Handles infinite scale automatically.
4.  **Snowflake**: Resize the Warehouse from X-Small to Medium (vertical scaling) or Multi-Cluster (horizontal scaling).

### Q4: "Why split Silver and Gold?"
**Answer**: 
*   **Silver** is for Data Scientists. They want clean, granular, flight-by-flight data to train ML models (e.g., predicting delays).
*   **Gold** is for Business Analysts / Dashboard. They just want "Total Flights per Country". They don't need billion rows; they need the pre-aggregated summary for speed.

---

## 🎯 Behavioral Strategy: "The Bug Story"
*Prepare this story. Interviewers love it.*

> "During the project, I noticed my **Gold Layer** timestamps were failing in Snowflake. 
> **The Problem**: Polars was inferring High-Precision Nanosecond timestamps, which Snowflake rejected.
> **The Debug**: I wrote a dedicated script `verify_snowflake_data.py` to inspect the raw types in the DB.
> **The Fix**: I implemented robust type coercion in the Gold asset, forcing seconds-precision.
> **The Lesson**: Always validate data types at the boundaries between systems (Python -> SQL)."
