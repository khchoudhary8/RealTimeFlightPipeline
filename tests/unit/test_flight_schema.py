"""
Tests for Pydantic flight data schemas.
These tests validate that our schemas catch malformed data correctly.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from schemas.flight_schema import FlightRecord, FlightBatch


class TestFlightRecord:
    """Test FlightRecord validation"""

    def test_valid_flight_passes(self):
        """A valid flight record should pass validation"""
        flight = FlightRecord(
            icao24="801642",
            callsign="AXB1124",
            origin_country="India",
            time_position=1753735222,
            longitude=75.8221,
            latitude=28.2676,
            baro_altitude=4892.04,
            velocity=161.18,
        )
        assert flight.icao24 == "801642"
        assert flight.longitude == 75.8221

    def test_validates_icao24_length(self):
        """icao24 must be exactly 6 characters"""
        with pytest.raises(ValidationError) as exc_info:
            FlightRecord(
                icao24="80164",  # Too short
                origin_country="India",
                time_position=1753735222,
                longitude=75.8221,
                latitude=28.2676,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("icao24",) for e in errors)

    def test_validates_icao24_hex(self):
        """icao24 must be valid hex string"""
        with pytest.raises(ValidationError) as exc_info:
            FlightRecord(
                icao24="GHIJKL",  # Not valid hex
                origin_country="India",
                time_position=1753735222,
                longitude=75.8221,
                latitude=28.2676,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("icao24",) for e in errors)

    def test_validates_latitude_range(self):
        """Latitude must be between -90 and 90"""
        with pytest.raises(ValidationError) as exc_info:
            FlightRecord(
                icao24="801642",
                origin_country="India",
                time_position=1753735222,
                longitude=75.8221,
                latitude=100.0,  # Invalid
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("latitude",) for e in errors)

    def test_validates_longitude_range(self):
        """Longitude must be between -180 and 180"""
        with pytest.raises(ValidationError) as exc_info:
            FlightRecord(
                icao24="801642",
                origin_country="India",
                time_position=1753735222,
                longitude=200.0,  # Invalid
                latitude=28.2676,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("longitude",) for e in errors)

    def test_validates_negative_longitude(self):
        """Negative longitudes are valid"""
        flight = FlightRecord(
            icao24="801642",
            origin_country="USA",
            time_position=1753735222,
            longitude=-122.4194,  # San Francisco
            latitude=37.7749,
        )
        assert flight.longitude == -122.4194

    def test_validates_timestamp_not_in_future(self):
        """Timestamp cannot be more than 1 hour in future"""
        future_timestamp = int(datetime.utcnow().timestamp()) + 7200  # 2 hours ahead
        with pytest.raises(ValidationError) as exc_info:
            FlightRecord(
                icao24="801642",
                origin_country="India",
                time_position=future_timestamp,
                longitude=75.8221,
                latitude=28.2676,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("time_position",) for e in errors)

    def test_validates_velocity_upper_bound(self):
        """Velocity cannot exceed realistic maximum (500 m/s)"""
        with pytest.raises(ValidationError) as exc_info:
            FlightRecord(
                icao24="801642",
                origin_country="India",
                time_position=1753735222,
                longitude=75.8221,
                latitude=28.2676,
                velocity=600.0,  # Too fast
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("velocity",) for e in errors)

    def test_strips_callsign_whitespace(self):
        """Callsign should have whitespace stripped"""
        flight = FlightRecord(
            icao24="801642",
            callsign="  AXB1124  ",
            origin_country="India",
            time_position=1753735222,
            longitude=75.8221,
            latitude=28.2676,
        )
        assert flight.callsign == "AXB1124"

    def test_converts_none_callsign(self):
        """None or empty callsign should become None"""
        flight = FlightRecord(
            icao24="801642",
            callsign="   ",
            origin_country="India",
            time_position=1753735222,
            longitude=75.8221,
            latitude=28.2676,
        )
        assert flight.callsign is None

    def test_allows_optional_fields_to_be_none(self):
        """baro_altitude and velocity can be None"""
        flight = FlightRecord(
            icao24="801642",
            origin_country="India",
            time_position=1753735222,
            longitude=75.8221,
            latitude=28.2676,
            baro_altitude=None,
            velocity=None,
        )
        assert flight.baro_altitude is None
        assert flight.velocity is None

    def test_model_dump_serializes_correctly(self):
        """model_dump should produce clean dict for Kafka"""
        flight = FlightRecord(
            icao24="801642",
            callsign="AXB1124",
            origin_country="India",
            time_position=1753735222,
            longitude=75.8221,
            latitude=28.2676,
            baro_altitude=4892.04,
            velocity=161.18,
        )
        data = flight.model_dump()
        assert data["icao24"] == "801642"
        assert data["longitude"] == 75.8221
        assert data["latitude"] == 28.2676


class TestFlightBatch:
    """Test FlightBatch validation"""

    def test_valid_batch_passes(self):
        """A batch with valid flights should pass"""
        flights = [
            FlightRecord(
                icao24="801642", origin_country="India", time_position=1753735222, longitude=75.8221, latitude=28.2676
            ),
            FlightRecord(
                icao24="123456", origin_country="India", time_position=1753735223, longitude=80.0, latitude=25.0
            ),
        ]
        batch = FlightBatch(flights=flights)
        assert len(batch) == 2

    def test_batch_must_have_at_least_one_flight(self):
        """Batch cannot be empty"""
        with pytest.raises(ValidationError) as exc_info:
            FlightBatch(flights=[])
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("flights",) for e in errors)

    def test_batch_contains_validated_flights(self):
        """All flights in batch should be validated"""
        with pytest.raises(ValidationError) as exc_info:
            FlightBatch(
                flights=[
                    FlightRecord(
                        icao24="801642",
                        origin_country="India",
                        time_position=1753735222,
                        longitude=75.8221,
                        latitude=28.2676,
                    ),
                    FlightRecord(
                        icao24="INVALID",  # Will fail validation
                        origin_country="India",
                        time_position=1753735222,
                        longitude=75.8221,
                        latitude=28.2676,
                    ),
                ]
            )
        # Should fail because one flight is invalid
        assert exc_info.value is not None

    def test_batch_dump_for_kafka(self):
        """Should produce list of dicts for Kafka"""
        flights = [
            FlightRecord(
                icao24="801642",
                callsign="AXB1124",
                origin_country="India",
                time_position=1753735222,
                longitude=75.8221,
                latitude=28.2676,
            )
        ]
        batch = FlightBatch(flights=flights)
        kafka_messages = batch.model_dump_for_kafka()
        assert len(kafka_messages) == 1
        assert kafka_messages[0]["icao24"] == "801642"


class TestSchemaIntegration:
    """Test schema integration scenarios"""

    def test_validates_mixed_valid_invalid_flights(self):
        """Batch validation should fail if any flight is invalid"""
        with pytest.raises(ValidationError):
            FlightBatch(
                flights=[
                    FlightRecord(
                        icao24="801642",  # Valid
                        origin_country="India",
                        time_position=1753735222,
                        longitude=75.8221,
                        latitude=28.2676,
                    ),
                    FlightRecord(
                        icao24="12345",  # Invalid (wrong length)
                        origin_country="India",
                        time_position=1753735222,
                        longitude=75.8221,
                        latitude=28.2676,
                    ),
                ]
            )

    def test_validates_edge_case_coordinates(self):
        """Test boundary coordinates"""
        flight = FlightRecord(
            icao24="801642",
            origin_country="India",
            time_position=1753735222,
            longitude=180.0,  # Max valid
            latitude=90.0,  # Max valid
        )
        assert flight.longitude == 180.0
        assert flight.latitude == 90.0

    def test_validates_zero_coordinates(self):
        """Zero coordinates should be valid"""
        flight = FlightRecord(
            icao24="801642",
            origin_country="Global",
            time_position=1753735222,
            longitude=0.0,  # Prime meridian
            latitude=0.0,  # Equator
        )
        assert flight.longitude == 0.0
        assert flight.latitude == 0.0
