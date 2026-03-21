
from orchestration.assets.silver import silver_flights
from orchestration.assets.gold import raw_flights_table
from unittest.mock import MagicMock, patch

@patch("orchestration.assets.silver.boto3")
@patch("orchestration.assets.silver.write_deltalake")
def test_silver_asset(mock_write_deltalake, mock_boto3):
    # Mock resources
    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3
    
    # Mock S3 list objects
    mock_s3.list_objects_v2.return_value = {
        'Contents': [{'Key': 'bronze/file1.json'}]
    }
    
    # Mock S3 get object
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: b'{"icao24": "abc", "longitude": 1.0, "latitude": 2.0, "time_position": 1600000000}')
    }
    
    # Run asset
    input_files = ["bronze/file1.json"]
    result = silver_flights(input_files)
    
    # Verify result
    assert result.value.startswith("s3://")
    assert result.metadata["rows_written"] == 1
    mock_write_deltalake.assert_called_once()

@patch("orchestration.assets.gold.DeltaTable")
@patch("orchestration.assets.gold.get_snowflake_connection")
@patch("orchestration.assets.gold.write_pandas")
def test_gold_asset(mock_write_pandas, mock_conn, mock_delta_table):
    # Mock inputs
    silver_path = "s3://bucket/silver/delta_flights"
    
    # Mock Delta Table data
    mock_dt_instance = MagicMock()
    mock_delta_table.return_value = mock_dt_instance
    
    import pandas as pd
    mock_df = pd.DataFrame([{
        "icao24": "abc",
        "longitude": 1.0, 
        "latitude": 2.0,
        "time_position": pd.Timestamp.now(),  # Delta table returns timestamps
        "velocity": 100.0,
        "baro_altitude": 1000.0,
        "callsign": "BA101",
        "origin_country": "UK"
    }])
    mock_dt_instance.to_pandas.return_value = mock_df
    
    # Mock Snowflake interactions
    mock_write_pandas.return_value = (True, 1, 1, [])
    
    # Run asset
    result = raw_flights_table(silver_path)
    
    # Verify
    assert result.value == 1
    assert result.metadata["snowflake_table"] == "FLIGHTS_RAW"
