"""Typed result models for ukgeolocate."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LookupResult:
    """Complete result of a postcode + address -> coordinate lookup."""

    uprn: int
    matched_address: str
    match_score: float       # 0.0-1.0 similarity confidence
    easting: float           # OS National Grid
    northing: float          # OS National Grid
    latitude: float          # WGS84
    longitude: float         # WGS84

    def to_dict(self) -> dict:
        """Convert to a plain dictionary (useful for JSON serialisation)."""
        return {
            "uprn": self.uprn,
            "matched_address": self.matched_address,
            "match_score": round(self.match_score, 3),
            "easting": self.easting,
            "northing": self.northing,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
