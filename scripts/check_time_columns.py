import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from scripts.verify_snowflake_data import get_snowflake_connection

conn = get_snowflake_connection()
cursor = conn.cursor()

try:
    # 1. Total row count
    cursor.execute("SELECT COUNT(*) FROM FLIGHTS_RAW")
    print(f"Total rows: {cursor.fetchone()[0]}")

    # 2. Check nulls for all time columns
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN TIME_POSITION IS NULL THEN 1 ELSE 0 END) as time_position_nulls,
            SUM(CASE WHEN PROCESSED_AT IS NULL THEN 1 ELSE 0 END) as processed_at_nulls,
            SUM(CASE WHEN PARTITION_DATE IS NULL THEN 1 ELSE 0 END) as partition_date_nulls
        FROM FLIGHTS_RAW
    """)
    row = cursor.fetchone()
    total = row[0] if row[0] else 1
    print(f"\n--- NULL Analysis ---")
    print(f"Total rows:            {row[0]}")
    print(f"TIME_POSITION nulls:   {row[1]} ({row[1]*100//total}%)")
    print(f"PROCESSED_AT nulls:    {row[2]} ({row[2]*100//total}%)")
    print(f"PARTITION_DATE nulls:  {row[3]} ({row[3]*100//total}%)")

    # 3. Check actual values (cast to varchar to avoid type issues)
    print(f"\n--- Time Value Samples ---")
    cursor.execute("""
        SELECT 
            TIME_POSITION::VARCHAR as tp, 
            PROCESSED_AT::VARCHAR as pa, 
            PARTITION_DATE::VARCHAR as pd
        FROM FLIGHTS_RAW 
        LIMIT 5
    """)
    for r in cursor.fetchall():
        print(f"TIME_POSITION={r[0]}  |  PROCESSED_AT={r[1]}  |  PARTITION_DATE={r[2]}")

    # 4. Check data types
    print(f"\n--- Column Data Types ---")
    cursor.execute("SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='FLIGHTS_RAW' ORDER BY ORDINAL_POSITION")
    for r in cursor.fetchall():
        print(f"  {r[0]:25s} {r[1]:20s} nullable={r[2]}")

    # 5. Check non-null time ranges using varchar cast
    print(f"\n--- Non-NULL Time Ranges ---")
    cursor.execute("""
        SELECT 
            MIN(TIME_POSITION::VARCHAR), MAX(TIME_POSITION::VARCHAR),
            MIN(PROCESSED_AT::VARCHAR), MAX(PROCESSED_AT::VARCHAR),
            MIN(PARTITION_DATE::VARCHAR), MAX(PARTITION_DATE::VARCHAR)
        FROM FLIGHTS_RAW 
        WHERE TIME_POSITION IS NOT NULL
    """)
    row = cursor.fetchone()
    print(f"TIME_POSITION:  {row[0]}  to  {row[1]}")
    print(f"PROCESSED_AT:   {row[2]}  to  {row[3]}")
    print(f"PARTITION_DATE: {row[4]}  to  {row[5]}")

finally:
    conn.close()
