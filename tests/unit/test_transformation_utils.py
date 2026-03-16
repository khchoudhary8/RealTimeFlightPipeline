"""
Tests for data transformation utilities in bronze_to_silver layer
"""

import pytest
import pandas as pd
from Faust.transformation_utils import (
    filter_valid_flights,
    transform_flight_data,
    parse_s3_key_timestamp,
    generate_silver_key,
)


class TestFilterValidFlights:
    """Test the flight filtering logic"""

    def test_returns_empty_for_empty_input(self):
        """Empty input returns empty list"""
        result = filter_valid_flights([])
        assert result == []

    def test_filters_records_with_missing_latitude(self):
        """Records without latitude are filtered out"""
        records = [
            {"icao24": "123", "longitude": 75.0, "latitude": None},
            {"icao24": "456", "longitude": 80.0, "latitude": 25.0},
        ]
        result = filter_valid_flights(records)
        assert len(result) == 1
        assert result[0]["icao24"] == "456"

    def test_filters_records_with_missing_longitude(self):
        """Records without longitude are filtered out"""
        records = [
            {"icao24": "123", "longitude": None, "latitude": 20.0},
            {"icao24": "456", "longitude": 80.0, "latitude": 25.0},
        ]
        result = filter_valid_flights(records)
        assert len(result) == 1
        assert result[0]["icao24"] == "456"

    def test_filters_records_with_both_missing(self):
        """Records with both coordinates missing are filtered out"""
        records = [
            {"icao24": "123", "longitude": None, "latitude": None},
            {"icao24": "456", "longitude": 80.0, "latitude": 25.0},
        ]
        result = filter_valid_flights(records)
        assert len(result) == 1

    def test_preserves_valid_records(self):
        """All valid records are preserved"""
        records = [
            {"icao24": "123", "longitude": 75.0, "latitude": 20.0},
            {"icao24": "456", "longitude": 80.0, "latitude": 25.0},
            {"icao24": "789", "longitude": 85.0, "latitude": 30.0},
        ]
        result = filter_valid_flights(records)
        assert len(result) == 3

    def test_handles_zero_coordinates(self):
        """Zero coordinates (0,0) are valid if they exist"""
        records = [
            {"icao24": "123", "longitude": 0.0, "latitude": 0.0},
            {"icao24": "456", "longitude": 80.0, "latitude": 25.0},
        ]
        result = filter_valid_flights(records)
        assert len(result) == 2


class TestTransformFlightData:
    """Test the DataFrame transformation logic"""

    def test_creates_dataframe_with_valid_records(self):
        """Valid records are transformed into DataFrame"""
        records = [
            {
                "icao24": "801642",
                "callsign": "AXB1124",
                "origin_country": "India",
                "time_position": 1753735222,
                "longitude": 75.8221,
                "latitude": 28.2676,
                "baro_altitude": 4892.04,
                "velocity": 161.18,
            }
        ]

        df = transform_flight_data(records)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["icao24"] == "801642"
        assert df.iloc[0]["longitude"] == 75.8221

    def test_adds_processed_at_timestamp(self):
        """processed_at column is added"""
        records = [{"icao24": "123", "longitude": 75.0, "latitude": 20.0}]
        df = transform_flight_data(records)
        assert "processed_at" in df.columns
        assert pd.notna(df.iloc[0]["processed_at"])

    def test_converts_time_position_to_datetime(self):
        """time_position (unix timestamp) is converted to datetime"""
        records = [
            {
                "icao24": "123",
                "longitude": 75.0,
                "latitude": 20.0,
                "time_position": 1704067200,  # 2024-01-01 00:00:00 UTC
            }
        ]
        df = transform_flight_data(records)
        assert pd.api.types.is_datetime64_any_dtype(df["time_position"])
        assert df.iloc[0]["time_position"].year == 2024

    def test_handles_missing_columns(self):
        """Missing optional columns are added as None"""
        records = [
            {"icao24": "123", "longitude": 75.0, "latitude": 20.0}  # Missing many fields
        ]
        df = transform_flight_data(records)
        # Should not raise error, missing columns become None
        assert "callsign" in df.columns
        assert df.iloc[0]["callsign"] is None

    def test_raises_error_for_no_valid_records(self):
        """Should raise ValueError if all records invalid"""
        records = [
            {"icao24": "123", "longitude": None, "latitude": 20.0},
            {"icao24": "456", "longitude": 75.0, "latitude": None},
        ]
        with pytest.raises(ValueError, match="No valid flight records"):
            transform_flight_data(records)

    def test_filters_out_invalid_coordinates(self):
        """Records with invalid coordinates are filtered"""
        records = [
            {"icao24": "123", "longitude": 75.0, "latitude": 20.0},
            {"icao24": "456", "longitude": None, "latitude": 25.0},
            {"icao24": "789", "longitude": 80.0, "latitude": 30.0},
        ]
        df = transform_flight_data(records)
        assert len(df) == 2
        icao24s = df["icao24"].tolist()
        assert "456" not in icao24s


class TestParseS3KeyTimestamp:
    """Test timestamp extraction from S3 keys"""

    def test_parses_standard_bronze_key(self):
        """Parse timestamp from standard bronze key"""
        key = "bronze/2024/01/15/143000_batch.json"
        ts = parse_s3_key_timestamp(key)
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15
        assert ts.hour == 14
        assert ts.minute == 30
        assert ts.second == 0

    def test_parses_flight_specific_key(self):
        """Parse timestamp from flights key"""
        key = "bronze/2024/01/15/143000_flights.json"
        ts = parse_s3_key_timestamp(key)
        assert ts == pd.Timestamp("2024-01-15 14:30:00")

    def test_returns_current_time_for_invalid_key(self):
        """Invalid key returns current time"""
        key = "invalid/key.json"
        ts = parse_s3_key_timestamp(key)
        # Should be recent (within last minute)
        assert (pd.Timestamp.utcnow() - ts).total_seconds() < 60


class TestGenerateSilverKey:
    """Test silver S3 key generation"""

    def test_generates_correct_partition_path(self):
        """Key includes YYYY/MM/DD/HH partition"""
        ts = pd.Timestamp("2024-01-15 14:30:00")
        key = generate_silver_key("silver_flights/", ts)
        assert "silver_flights/2024/01/15/14/" in key

    def test_uses_parquet_format(self):
        """Generated key uses .parquet extension"""
        ts = pd.Timestamp("2024-01-15 14:30:00")
        key = generate_silver_key("silver_flights/", ts)
        assert key.endswith(".parquet")

    def test_includes_timestamp_in_filename(self):
        """Filename includes precise timestamp"""
        ts = pd.Timestamp("2024-01-15 14:30:45")
        key = generate_silver_key("silver_flights/", ts)
        assert "flights_20240115143045.parquet" in key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
