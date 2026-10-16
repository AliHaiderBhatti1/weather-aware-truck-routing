"""Builders for synthetic routes used across geo/trip tests."""

from __future__ import annotations

from apps.geo.types import Route
from apps.geo.units import miles_to_meters

# ~1 degree of longitude at the equator is ~69 miles; we keep routes on lat 0
# so the haversine distance of each segment is predictable.
MILES_PER_DEGREE_LON_AT_EQUATOR = 69.0932


def straight_route(
    route_id: str = "r",
    total_miles: float = 100.0,
    segments: int = 10,
    mph: float = 50.0,
    lat: float = 0.0,
    lon_start: float = 0.0,
    source: str = "fastest",
) -> Route:
    """A straight east-west route split into equal segments at constant speed."""
    seg_miles = total_miles / segments
    seg_deg = seg_miles / MILES_PER_DEGREE_LON_AT_EQUATOR
    coords = [(lon_start + i * seg_deg, lat) for i in range(segments + 1)]
    seg_m = miles_to_meters(seg_miles)
    seg_s = seg_miles / mph * 3600
    return Route(
        id=route_id,
        name=f"Test {route_id}",
        source=source,
        distance_m=seg_m * segments,
        duration_s=seg_s * segments,
        coordinates=coords,
        segment_distances_m=[seg_m] * segments,
        segment_durations_s=[seg_s] * segments,
    )
