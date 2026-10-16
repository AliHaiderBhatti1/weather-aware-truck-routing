"""Plain data types for places and routes, independent of any provider."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from apps.geo.units import meters_to_miles

EARTH_RADIUS_M = 6_371_008.8


@dataclass(frozen=True, slots=True)
class GeoPoint:
    lat: float
    lon: float

    def distance_to(self, other: GeoPoint) -> float:
        """Great-circle distance in metres (haversine)."""
        phi1, phi2 = math.radians(self.lat), math.radians(other.lat)
        dphi = phi2 - phi1
        dlmb = math.radians(other.lon - self.lon)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
        return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))

    def rounded(self, places: int = 4) -> GeoPoint:
        return GeoPoint(round(self.lat, places), round(self.lon, places))


@dataclass(frozen=True, slots=True)
class Place:
    name: str
    full_name: str
    point: GeoPoint
    kind: str = "place"


@dataclass(frozen=True, slots=True)
class Route:
    """
    A driveable route as returned by a routing provider.

    ``coordinates`` is the full-resolution polyline as ``(lon, lat)`` pairs.
    ``segment_distances_m`` / ``segment_durations_s`` have one entry per
    consecutive coordinate pair (``len(coordinates) - 1``) so travel time can be
    interpolated at any point along the line.
    """

    id: str
    name: str
    source: str
    distance_m: float
    duration_s: float
    coordinates: list[tuple[float, float]]
    segment_distances_m: list[float]
    segment_durations_s: list[float]

    def __post_init__(self) -> None:
        expected = max(len(self.coordinates) - 1, 0)
        if len(self.segment_distances_m) != expected or len(self.segment_durations_s) != expected:
            raise ValueError("Route annotations must have one entry per coordinate pair")

    @property
    def distance_miles(self) -> float:
        return meters_to_miles(self.distance_m)

    @property
    def origin(self) -> GeoPoint:
        lon, lat = self.coordinates[0]
        return GeoPoint(lat, lon)

    @property
    def destination(self) -> GeoPoint:
        lon, lat = self.coordinates[-1]
        return GeoPoint(lat, lon)


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """A point along a route where weather is sampled, with the truck's ETA there."""

    index: int
    point: GeoPoint
    distance_from_start_miles: float
    elapsed_seconds: float
    eta: datetime
    segment_miles: float = field(default=0.0)
    """Miles from this checkpoint to the next one (0 for the final checkpoint)."""
