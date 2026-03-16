"""
Tests for flight data production and processing
"""

import pytest
from unittest.mock import MagicMock

# Import the function we want to test
from OpenSky.flight_producer import fetch_flight_data


class TestFetchFlightData:
    """Test the flight data fetching functionality"""

    def test_returns_list_on_success(self, monkeypatch):
        """Test that fetch_flight_data returns a list"""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"states": [["801642", "AXB1124", "India", 1753735222, null, 75.8221, 28.2676, 4892.04, null, 161.18, null]]}'
        mock_response.json.return_value = {
            "states": [["801642", "AXB1124", "India", 1753735222, None, 75.8221, 28.2676, 4892.04, None, 161.18, None]]
        }

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: mock_response)

        result = fetch_flight_data()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["icao24"] == "801642"

    def test_filters_india_bounds(self, monkeypatch):
        """Test that only flights within India bounds are returned"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "states": [
                # Inside India bounds
                ["801642", "AXB1124", "India", 1753735222, None, 75.8221, 28.2676, 4892.04, None, 161.18, None],
                # Outside India bounds (too far north)
                ["123456", "TEST123", "Pakistan", 1753735223, None, 75.0, 40.0, 5000.0, None, 200.0, None],
                # Outside India bounds (too far south)
                ["789012", "TEST456", "Sri Lanka", 1753735224, None, 80.0, 5.0, 3000.0, None, 150.0, None],
            ]
        }

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: mock_response)

        result = fetch_flight_data()

        # Should only return the India flight
        assert len(result) == 1
        assert result[0]["icao24"] == "801642"

    def test_handles_timeout(self, monkeypatch):
        """Test that timeout returns empty list"""
        import requests

        def raise_timeout(*args, **kwargs):
            raise requests.exceptions.Timeout()

        monkeypatch.setattr("requests.get", raise_timeout)

        result = fetch_flight_data()

        assert result == []

    def test_handles_request_exception(self, monkeypatch):
        """Test that network errors return empty list"""
        import requests

        def raise_error(*args, **kwargs):
            raise requests.exceptions.RequestException("Network error")

        monkeypatch.setattr("requests.get", raise_error)

        result = fetch_flight_data()

        assert result == []

    def test_handles_empty_response(self, monkeypatch):
        """Test that empty API response returns empty list"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"states": []}

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: mock_response)

        result = fetch_flight_data()

        assert result == []

    def test_handles_malformed_data(self, monkeypatch):
        """Test that malformed flight data is skipped"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "states": [
                # Valid flight
                ["801642", "AXB1124", "India", 1753735222, None, 75.8221, 28.2676, 4892.04, None, 161.18, None],
                # Incomplete data (too short)
                ["123"],  # Only one element
                # Missing coordinates
                ["789012", "TEST456", "India", 1753735224, None, None, 28.0, 3000.0, None, 150.0, None],
            ]
        }

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: mock_response)

        result = fetch_flight_data()

        # Only the valid flight should be returned
        assert len(result) == 1
        assert result[0]["icao24"] == "801642"

    def test_strips_callsign(self, monkeypatch):
        """Test that callsigns are stripped of whitespace"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "states": [
                # Callsign with spaces
                ["801642", "  AXB1124  ", "India", 1753735222, None, 75.8221, 28.2676, 4892.04, None, 161.18, None],
            ]
        }

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: mock_response)

        result = fetch_flight_data()

        assert result[0]["callsign"] == "AXB1124"  # No leading/trailing spaces

    def test_handles_none_callsign(self, monkeypatch):
        """Test that None callsign is handled"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "states": [
                ["801642", None, "India", 1753735222, None, 75.8221, 28.2676, 4892.04, None, 161.18, None],
            ]
        }

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: mock_response)

        result = fetch_flight_data()

        assert result[0]["callsign"] is None


class TestStreamFlights:
    """Test the streaming functionality"""

    @pytest.mark.skip(reason="Integration test - requires running Kafka")
    def test_stream_flights_integration(self):
        """Integration test - requires actual Kafka"""
        # This would be an integration test
        # For now, we mark it as skip
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
