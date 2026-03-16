"""
Data transformation functions for Bronze to Silver layer.
These are pure functions that can be tested without AWS credentials.
"""

import pandas as pd
from typing import List, Dict, Any


def filter_valid_flights(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter flight records to only include those with valid longitude and latitude.

    Args:
        records: List of flight record dictionaries

    Returns:
        List of records with valid coordinates

    Example:
        >>> records = [
        ...     {"icao24": "123", "longitude": 75.0, "latitude": 20.0},
        ...     {"icao24": "456", "longitude": None, "latitude": 25.0}
        ... ]
        >>> filter_valid_flights(records)
        [{'icao24': '123', 'longitude': 75.0, 'latitude': 20.0}]
    """
    valid = []
    for record in records:
        lon = record.get("longitude")
        lat = record.get("latitude")
        if lon is not None and lat is not None:
            valid.append(record)
    return valid


def transform_flight_data(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Transform raw flight records into a cleaned DataFrame.

    Args:
        records: List of flight record dictionaries

    Returns:
        Pandas DataFrame with standardized schema

    Raises:
        ValueError: If no valid records after filtering
    """
    # Filter valid records
    valid_records = filter_valid_flights(records)

    if not valid_records:
        raise ValueError("No valid flight records with coordinates")

    # Create DataFrame
    df = pd.DataFrame(valid_records)

    # Define expected columns (from flight schema)
    expected_cols = [
        "icao24",
        "callsign",
        "origin_country",
        "time_position",
        "longitude",
        "latitude",
        "baro_altitude",
        "velocity",
    ]

    # Add missing columns as None
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    # Convert time_position to datetime if exists and is numeric (unix timestamp)
    if "time_position" in df.columns:
        # Handle both numeric timestamps and existing datetime
        if pd.api.types.is_numeric_dtype(df["time_position"]):
            df["time_position"] = pd.to_datetime(df["time_position"], unit="s", errors="coerce")

    # Add metadata columns
    df["processed_at"] = pd.Timestamp.utcnow()

    return df


def parse_s3_key_timestamp(key: str) -> pd.Timestamp:
    """
    Extract timestamp from S3 key.

    Example keys:
    - bronze/2024/01/15/143000_batch.json
    - bronze/2024/01/15/143000_flights.json

    Returns:
        pd.Timestamp parsed from the key
    """
    import re

    # Extract YYYY/MM/DD/HHMMSS pattern
    match = re.search(r"(\d{4}/\d{2}/\d{2}/\d{6})", key)
    if match:
        datepart = match.group(1)
        # Remove slashes to get YYYYMMDDHHMMSS
        dt_str = datepart.replace("/", "")
        return pd.to_datetime(dt_str, format="%Y%m%d%H%M%S")
    return pd.Timestamp.utcnow()


def generate_silver_key(base_path: str, timestamp: pd.Timestamp) -> str:
    """
    Generate S3 key for silver layer with partitioning.

    Args:
        base_path: Silver prefix (e.g., 'silver_flights/')
        timestamp: Timestamp for partitioning

    Returns:
        S3 key with partition path
    """
    partition_path = timestamp.strftime("%Y/%m/%d/%H")
    filename = f"flights_{timestamp.strftime('%Y%m%d%H%M%S')}.parquet"
    return f"{base_path}{partition_path}/{filename}"
