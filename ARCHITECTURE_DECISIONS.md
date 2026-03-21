# 🏗️ Architecture Justification: Why This Stack?

This document answers the critical interview question:
> *"Why did you use Kafka, Dagster, S3, and Snowflake for a simple flight tracker? Couldn't a Python script just insert into a database?"*

## The Short Answer
**A simple script is fragile and unscalable.**
This architecture is built for **Resilience**, **Scalability**, and **Maintainability**. It solves problems that appear *after* Day 1 production.

---

## 1. Why Kafka? 📨 (Decoupling & buffering)
**Alternative**: Direct API -> Database.
**Problem**:
- What if the Database is down for maintenance? The API script crashes, and you lose data.
- What if API traffic spikes to 100k msg/sec? The DB can't write fast enough, and the script crashes.
**Solution**:
- Kafka acts as a **Buffer**. It holds data safely until the consumer is ready.
- It **Decouples** systems. The Producer doesn't need to know the Database exists.

## 2. Why S3 (Data Lake)? 💾 (Source of Truth)
**Alternative**: Delete raw data after processing.
**Problem**:
- You discover a bug in your parsing logic 2 months later. The original data is gone. You can't fix it.
**Solution**:
- S3 stores **Raw History (Bronze)** forever. It's cheap.
- If you mess up Silver/Gold, you just **Replay** processing from S3. You can't do that with a simple DB insert.

## 3. Why Medallion Architecture? 🥇 (Data Quality)
**Alternative**: One big table for everything.
**Problem**:
- Mixing raw, messy data with clean, aggregated data makes analytics slow and error-prone.
- "Garbage In, Garbage Out".
**Solution**:
- **Bronze (Raw)**: Exact copy of source. No loss.
- **Silver (Clean)**: Deduplicated, types fixed, errors removed. Usable.
- **Gold (Aggregated)**: Business-level metrics (e.g., "Daily Flights"). Fast for Dashboards.

## 4. Why Dagster? ⚙️ (Orchestration vs Cron)
**Alternative**: A cron job running `python script.py`.
**Problem**:
- What if it fails at 3 AM? Cron won't tell you.
- What if step 2 depends on step 1, but step 1 failed? Cron runs step 2 anyway, corrupting data.
**Solution**:
- Dagster manages **Dependencies**. It knows *not* to run Silver if Bronze failed.
- It provides **Observability**, **Retries**, and **Backfills**.

## 5. Why Snowflake? ❄️ (Separation of Compute & Storage)
**Alternative**: PostgreSQL / MySQL.
**Problem**:
- To run a massive query, you slow down the transactional DB for everyone else.
- Scaling requires buying a bigger server (Vertical Scaling).
**Solution**:
- Snowflake separates **Storage** (S3) from **Compute** (Warehouses).
- You can spin up a "Mega Warehouse" for 5 minutes of crunching, then shut it down.

---

## Summary Table

| Component | Solves Problem | "Simple Script" Risk |
| :--- | :--- | :--- |
| **Kafka** | Backpressure & Decoupling | Data loss during spikes/outages. |
| **S3** | Replayability & History | Bugs in logic destroy historical data irrecoverably. |
| **Dagster** | Dependency Management | Silent failures, corrupted downstream data. |
| **Snowflake** | Analytical Scale | Reporting queries kills the application DB. |
