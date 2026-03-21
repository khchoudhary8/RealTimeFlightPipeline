"""
Tests for bronze_to_silver transformation.
Tests cover pure logic without needing real AWS credentials.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock
from Faust.bronze_to_silver import BronzeToSilverTransformer, transform_bronze_to_silver


class TestBronzeToSilverTransformer:
    """Test the BronzeToSilverTransformer class"""

    @pytest.fixture
    def mock_s3(self):
        """Create a mock S3 client"""
        s3 = MagicMock()
        return s3

    @pytest.fixture
    def transformer(self, mock_s3):
        """Create transformer with mock S3"""
        return BronzeToSilverTransformer(
            s3_client=mock_s3, bucket_name="test-bucket", bronze_prefix="bronze/", silver_prefix="silver_flights/"
        )

    def test_list_bronze_keys_empty(self, transformer, mock_s3):
        """Should handle empty S3 response"""
        mock_s3.list_objects_v2.return_value = {}
        keys = transformer.list_bronze_keys()
        assert keys == []

    def test_list_bronze_keys_with_files(self, transformer, mock_s3):
        """Should extract JSON keys from response"""
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "bronze/file1.json"},
                {"Key": "bronze/file2.json"},
                {"Key": "bronze/file3.txt"},  # Should be filtered out
            ]
        }
        keys = transformer.list_bronze_keys()
        assert len(keys) == 2
        assert "bronze/file1.json" in keys
        assert "bronze/file2.json" in keys

    def test_read_json_from_s3_single(self, transformer, mock_s3):
        """Should read single JSON object"""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=lambda: json.dumps(
                    {
                        "icao24": "801642",
                        "callsign": "TEST123",
                        "origin_country": "India",
                        "time_position": 1753735222,
                        "longitude": 75.8221,
                        "latitude": 28.2676,
                        "baro_altitude": 4892.04,
                        "velocity": 161.18,
                    }
                ).encode("utf-8")
            )
        }
        data = transformer.read_json_from_s3("bronze/test.json")
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["icao24"] == "801642"

    def test_read_json_from_s3_array(self, transformer, mock_s3):
        """Should read JSON array"""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=lambda: json.dumps(
                    [
                        {
                            "icao24": "123456",
                            "callsign": "TEST001",
                            "origin_country": "India",
                            "time_position": 1753735222,
                            "longitude": 75.0,
                            "latitude": 20.0,
                        },
                        {
                            "icao24": "789012",
                            "callsign": "TEST002",
                            "origin_country": "India",
                            "time_position": 1753735223,
                            "longitude": 80.0,
                            "latitude": 25.0,
                        },
                    ]
                ).encode("utf-8")
            )
        }
        data = transformer.read_json_from_s3("bronze/test.json")
        assert len(data) == 2

    def test_process_file_extracts_valid_flights(self, transformer, mock_s3):
        """Should extract only flights with valid coordinates"""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=lambda: json.dumps(
                    [
                        {
                            "icao24": "801642",
                            "callsign": "TEST001",
                            "origin_country": "India",
                            "time_position": 1753735222,
                            "longitude": 75.8221,
                            "latitude": 28.2676,
                        },
                        {
                            "icao24": "123456",
                            "callsign": "TEST002",
                            "origin_country": "India",
                            "time_position": 1753735223,
                            "longitude": None,
                            "latitude": 25.0,
                        },
                        {
                            "icao24": "789012",
                            "callsign": "TEST003",
                            "origin_country": "India",
                            "time_position": 1753735224,
                            "longitude": 80.0,
                            "latitude": 30.0,
                        },
                    ]
                ).encode("utf-8")
            )
        }
        records = transformer.process_file("bronze/test.json")
        assert len(records) == 2
        assert records[0]["icao24"] == "801642"
        assert records[1]["icao24"] == "789012"

    def test_process_file_handles_malformed_json(self, transformer, mock_s3):
        """Should raise error for malformed JSON"""
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"invalid json")}
        with pytest.raises(json.JSONDecodeError):
            transformer.process_file("bronze/test.json")

    def test_write_to_silver_validates_schema(self, transformer, mock_s3):
        """Should validate records with Pydantic before writing"""
        valid_records = [
            {
                "icao24": "801642",
                "callsign": "TEST123",
                "origin_country": "India",
                "time_position": 1753735222,
                "longitude": 75.8221,
                "latitude": 28.2676,
                "baro_altitude": 4892.04,
                "velocity": 161.18,
            }
        ]
        timestamp = datetime.utcnow()

        output_key = transformer.write_to_silver(valid_records, timestamp)

        assert output_key.startswith("silver_flights/")
        assert output_key.endswith(".parquet")
        assert mock_s3.put_object.called

    def test_write_to_silver_rejects_invalid_schema(self, transformer, mock_s3):
        """Should reject records that fail schema validation"""
        invalid_records = [
            {
                "icao24": "INVALID",  # Should be 6 hex chars
                "callsign": "TEST",
                "origin_country": "India",
                "time_position": 1753735222,
                "longitude": 75.8221,
                "latitude": 28.2676,
            }
        ]
        timestamp = datetime.utcnow()

        with pytest.raises(ValueError, match="Schema validation failed"):
            transformer.write_to_silver(invalid_records, timestamp)

    def test_write_to_silver_rejects_empty_records(self, transformer, mock_s3):
        """Should reject empty records list"""
        with pytest.raises(ValueError, match="Cannot write empty records"):
            transformer.write_to_silver([], datetime.utcnow())

    def test_transform_all_success(self, transformer, mock_s3):
        """Should transform all bronze files successfully"""
        # Mock list_objects
        mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "bronze/file1.json"}]}

        # Mock get_object
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=lambda: json.dumps(
                    [
                        {
                            "icao24": "801642",
                            "callsign": "TEST001",
                            "origin_country": "India",
                            "time_position": 1753735222,
                            "longitude": 75.8221,
                            "latitude": 28.2676,
                        }
                    ]
                ).encode("utf-8")
            )
        }

        result = transformer.transform_all()

        assert result["success"] is True
        assert result["keys_processed"] == 1
        assert result["total_records"] == 1
        assert "output_key" in result
        assert result["errors"] == []

    def test_transform_all_with_errors(self, transformer, mock_s3):
        """Should continue processing even if some files fail"""
        mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "bronze/good.json"}, {"Key": "bronze/bad.json"}]}

        def get_object_side_effect(Bucket, Key):
            if Key == "bronze/good.json":
                return {
                    "Body": MagicMock(
                        read=lambda: json.dumps(
                            [
                                {
                                    "icao24": "801642",
                                    "callsign": "TEST001",
                                    "origin_country": "India",
                                    "time_position": 1753735222,
                                    "longitude": 75.8221,
                                    "latitude": 28.2676,
                                }
                            ]
                        ).encode("utf-8")
                    )
                }
            else:
                raise Exception("Simulated S3 error")

        mock_s3.get_object.side_effect = get_object_side_effect
        mock_s3.put_object.return_value = {}

        result = transformer.transform_all()

        assert result["success"] is True
        assert result["keys_processed"] == 1
        assert result["total_records"] == 1
        assert len(result["errors"]) == 1
        assert "bad.json" in result["errors"][0]["key"]

    def test_transform_all_no_valid_records(self, transformer, mock_s3):
        """Should fail gracefully if no valid records"""
        mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "bronze/file.json"}]}
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=lambda: json.dumps(
                    [
                        {
                            "icao24": "801642",
                            "callsign": "TEST001",
                            "origin_country": "India",
                            "time_position": 1753735222,
                            "longitude": None,  # Invalid
                            "latitude": 28.2676,
                        }
                    ]
                ).encode("utf-8")
            )
        }

        result = transformer.transform_all()

        assert result["success"] is False
        assert result["total_records"] == 0
        assert "No valid records" in result["error"]

    def test_transform_all_empty_bronze(self, transformer, mock_s3):
        """Should handle empty bronze layer (no objects)"""
        mock_s3.list_objects_v2.return_value = {}

        result = transformer.transform_all()

        assert result["success"] is True  # Empty is considered success (nothing to process)
        assert result["keys_processed"] == 0
        assert result["total_records"] == 0


class TestConvenienceFunction:
    """Test the convenience function"""

    @pytest.fixture
    def mock_s3(self):
        s3 = MagicMock()
        return s3

    def test_transform_bronze_to_silver_function(self, mock_s3):
        """Convenience function should work"""
        mock_s3.list_objects_v2.return_value = {"Contents": []}

        result = transform_bronze_to_silver(s3_client=mock_s3, bucket_name="test-bucket")

        assert "success" in result
        assert result["success"] is True  # Empty is still success


class TestIntegrationScenario:
    """Integration-style tests with realistic data"""

    @pytest.fixture
    def mock_s3(self):
        s3 = MagicMock()
        return s3

    def test_full_pipeline_with_mixed_data(self, mock_s3):
        """Test realistic scenario with mixed valid/invalid data"""
        transformer = BronzeToSilverTransformer(s3_client=mock_s3, bucket_name="realtimeflightstreamingbuckett")

        # Mock S3 to return 3 files with mixed data
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "bronze/2024/01/15/100000_batch.json"},
                {"Key": "bronze/2024/01/15/100100_batch.json"},
                {"Key": "bronze/2024/01/15/100200_batch.json"},
            ]
        }

        def get_object_side_effect(Bucket, Key):
            if Key == "bronze/2024/01/15/100000_batch.json":
                # File with 3 flights, 1 invalid (no coordinates)
                return {
                    "Body": MagicMock(
                        read=lambda: json.dumps(
                            [
                                {
                                    "icao24": "801642",
                                    "callsign": "FLT001",
                                    "origin_country": "India",
                                    "time_position": 1753735222,
                                    "longitude": 75.8221,
                                    "latitude": 28.2676,
                                },
                                {
                                    "icao24": "123456",
                                    "callsign": "FLT002",
                                    "origin_country": "India",
                                    "time_position": 1753735223,
                                    "longitude": None,
                                    "latitude": 25.0,
                                },
                                {
                                    "icao24": "789012",
                                    "callsign": "FLT003",
                                    "origin_country": "India",
                                    "time_position": 1753735224,
                                    "longitude": 80.0,
                                    "latitude": 30.0,
                                },
                            ]
                        ).encode("utf-8")
                    )
                }
            elif Key == "bronze/2024/01/15/100100_batch.json":
                # Empty file
                return {"Body": MagicMock(read=lambda: b"[]")}
            else:
                # All valid
                return {
                    "Body": MagicMock(
                        read=lambda: json.dumps(
                            [
                                {
                                    "icao24": "456789",
                                    "callsign": "FLT004",
                                    "origin_country": "India",
                                    "time_position": 1753735225,
                                    "longitude": 85.0,
                                    "latitude": 27.0,
                                }
                            ]
                        ).encode("utf-8")
                    )
                }

        mock_s3.get_object.side_effect = get_object_side_effect
        mock_s3.put_object.return_value = {}

        result = transformer.transform_all()

        assert result["success"] is True
        assert result["total_records"] == 3  # 2 from file1 + 1 from file3
        assert result["keys_processed"] == 3
        # Empty array file is considered processed successfully (0 records)
        assert "output_key" in result

    def test_partitioning_structure(self, mock_s3):
        """Verify output S3 key uses correct partitioning"""
        transformer = BronzeToSilverTransformer(
            s3_client=mock_s3, bucket_name="test-bucket", silver_prefix="silver_delta/"
        )

        # Create sample data with all required fields
        records = [
            {
                "icao24": "801642",
                "callsign": "TEST123",
                "origin_country": "India",
                "time_position": 1753735222,
                "longitude": 75.8221,
                "latitude": 28.2676,
            }
        ]

        # Mock put_object
        mock_s3.put_object.return_value = {}

        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        output_key = transformer.write_to_silver(records, timestamp)

        # Verify partitioning
        assert output_key == "silver_delta/2024/01/15/10/flights_20240115103000.parquet"

        # Verify put_object was called correctly
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == output_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
