# 🏆 Gold Layer Setup Guide

This guide will help you set up the Gold layer (Snowflake integration) for your flight data pipeline.

## Prerequisites

1. **Snowflake Account**: You need a Snowflake account (free trial available)
2. **AWS S3 Access**: Your Snowflake account needs access to your S3 bucket
3. **Environment Variables**: Update your `.env` file with Snowflake credentials

## Step 1: Get Snowflake Credentials

1. **Sign up for Snowflake** (if you don't have an account):
   - Go to https://signup.snowflake.com/
   - Create a free trial account

2. **Get your account identifier**:
   - In Snowflake web interface, go to Admin → Accounts
   - Copy your account identifier (e.g., `abc12345.us-east-1`)

3. **Create a user and password**:
   - Go to Admin → Users
   - Create a new user or use existing credentials

## Step 2: Update Environment Variables

Edit your `.env` file with your Snowflake credentials:

```bash
# Snowflake Configuration
SNOWFLAKE_USER=KHCHOUDHARY8
SNOWFLAKE_PASSWORD=8409734394Kh$@
SNOWFLAKE_ACCOUNT=SIZUJDG-YT23888
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=FLIGHT_ANALYTICS
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

## Step 3: Install Dependencies

Make sure you have the Snowflake connector installed:

```bash
pip install snowflake-connector-python
```

## Step 4: Test the Gold Layer

Run the silver to gold transformation:

```bash
python Faust/silver_to_gold.py
```

This will:
- Create the `FLIGHT_ANALYTICS` database
- Create the `flights_raw` table
- Create analytics views
- Load your silver layer data into Snowflake

## Step 5: View Analytics Dashboard

Run the analytics dashboard:

```bash
python Faust/analytics_dashboard.py
```

This will show you:
- Daily flight summaries
- Country breakdown
- Top airlines
- Altitude and velocity statistics
- Hourly activity patterns

## Step 6: Run Complete Pipeline

To run the entire pipeline from bronze to gold:

```bash
python run_complete_pipeline.py
```

## Troubleshooting

### Common Issues:

1. **Connection Failed**:
   - Check your account identifier format
   - Verify username and password
   - Ensure your IP is whitelisted in Snowflake

2. **Permission Denied**:
   - Make sure you're using the correct role
   - Check if you have CREATE DATABASE permissions

3. **S3 Access Issues**:
   - Verify your AWS credentials in `.env`
   - Check if S3 bucket exists and is accessible

### Testing Connection:

You can test your Snowflake connection with this simple script:

```python
import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

conn = snowflake.connector.connect(
    user=os.getenv('SNOWFLAKE_USER'),
    password=os.getenv('SNOWFLAKE_PASSWORD'),
    account=os.getenv('SNOWFLAKE_ACCOUNT'),
    warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')
)

cursor = conn.cursor()
cursor.execute("SELECT CURRENT_VERSION()")
print(cursor.fetchone())
cursor.close()
conn.close()
```

## Next Steps

Once the Gold layer is working:

1. **Set up Tableau/PowerBI**: Connect to your Snowflake database
2. **Create Dashboards**: Build visualizations for flight analytics
3. **Set up Monitoring**: Add alerts for data quality issues
4. **Scale Up**: Consider partitioning and clustering for better performance

## Analytics Views Available

Your Snowflake database will include these pre-built views:

- `daily_flight_counts`: Daily flight statistics by country
- `hourly_flight_activity`: Hourly flight patterns
- `top_airlines`: Top airlines by flight count

## Data Schema

The `flights_raw` table includes:
- `icao24`: Aircraft identifier
- `callsign`: Flight callsign
- `origin_country`: Country of origin
- `time_position`: Timestamp
- `longitude`, `latitude`: Position coordinates
- `baro_altitude`: Altitude in meters
- `velocity`: Speed in m/s
- `processed_at`: Processing timestamp
- `partition_date`: Date partition for optimization

