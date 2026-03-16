"""
Pydantic schemas for flight data validation.
These schemas ensure data quality and catch malformed records early.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class FlightRecord(BaseModel):
    """
    Validated flight record schema.

    This schema ensures:
    - Required fields are present
    - Data types are correct
    - Geographic coordinates are within valid ranges
    - ICAO24 is properly formatted
    """

    icao24: str = Field(..., min_length=6, max_length=6, description="6-digit hex ICAO aircraft address")
    callsign: Optional[str] = Field(None, description="Flight callsign (may be null)")
    origin_country: str = Field(..., description="Country of origin")
    time_position: int = Field(..., gt=0, description="Unix timestamp of position")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    baro_altitude: Optional[float] = Field(None, ge=0, description="Barometric altitude in meters")
    velocity: Optional[float] = Field(None, ge=0, description="Ground speed in m/s")

    @field_validator("icao24")
    @classmethod
    def validate_icao24_hex(cls, v: str) -> str:
        """Ensure icao24 is a valid 6-character hex string"""
        if len(v) != 6:
            raise ValueError("icao24 must be exactly 6 characters")
        try:
            int(v, 16)  # Validate it's a hex string
        except ValueError:
            raise ValueError("icao24 must be a valid hex string")
        return v.lower()  # Normalize to lowercase

    @field_validator("callsign")
    @classmethod
    def validate_callsign(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from callsign if present"""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("time_position")
    @classmethod
    def validate_timestamp_reasonable(cls, v: int) -> int:
        """Ensure timestamp is within reasonable range (not in future, not too old)"""
        current_time = int(datetime.utcnow().timestamp())
        one_year_ago = current_time - (365 * 24 * 3600)

        if v > current_time + 3600:
            raise ValueError("timestamp is more than 1 hour in future")
        if v < one_year_ago:
            raise ValueError("timestamp is more than 1 year old")
        return v

    @field_validator("velocity")
    @classmethod
    def validate_velocity_reasonable(cls, v: Optional[float]) -> Optional[float]:
        """Ensure velocity is within realistic bounds"""
        if v is not None:
            if v > 500:  # ~Mach 1.5
                raise ValueError(f"velocity {v} m/s exceeds realistic maximum")
        return v

    def model_dump_for_kafka(self) -> dict:
        """Convert to dict suitable for Kafka serialization"""
        data = self.model_dump()
        # Convert datetime if needed (we store as int)
        return data


class FlightBatch(BaseModel):
    """
    Batch of flight records for validation.
    Useful for validating collections of flights.
    """

    flights: list[FlightRecord] = Field(..., min_length=1)
    batch_timestamp: datetime = Field(default_factory=datetime.utcnow)

    def __len__(self) -> int:
        return len(self.flights)

    def model_dump_for_kafka(self) -> list[dict]:
        """Convert all flights to dicts for Kafka"""
        return [flight.model_dump_for_kafka() for flight in self.flights]
