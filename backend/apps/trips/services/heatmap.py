"""
Corridor heatmap: a grid of forecast points around the routes, each carrying a
risk level for every hour of the 0-48 h window so the client can scrub through
time without further requests.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings

from apps.geo.types import GeoPoint
from apps.geo.units import miles_to_meters
from apps.risk.engine import assess
from apps.weather.client import RISK_ONLY_FIELDS
from apps.weather.service import WeatherService

MIN_SPACING_DEG = 0.08
TARGET_COLUMNS = 26
CORRIDOR_HALF_WIDTH_MILES = 35.0
ROUTE_SAMPLE_STEP = 8  # take every n-th vertex of the simplified geometry for distance tests


def build_heatmap(
    plan: dict[str, Any],
    *,
    weather: WeatherService | None = None,
    max_points: int | None = None,
) -> dict[str, Any]:
    weather = weather or WeatherService()
    max_points = max_points or settings.HEATMAP_MAX_POINTS

    routes_coords: list[list[list[float]]] = [
        route["geometry"]["coordinates"] for route in plan["routes"]
    ]
    load_lb = int(plan["request"]["load_weight_lb"])
    start = datetime.fromisoformat(plan["forecast_window"]["start"])
    hours = int(plan["forecast_window"]["hours"])
    end = start + timedelta(hours=hours)

    grid = corridor_grid(routes_coords, plan["bounds"], max_points=max_points)
    series = weather.hourly(grid, start, end, fields=RISK_ONLY_FIELDS)

    times = [start + timedelta(hours=i) for i in range(hours + 1)]
    points: list[dict[str, Any]] = []
    for point, hourly in zip(grid, series, strict=True):
        levels: list[int] = []
        winds: list[float] = []
        for moment in times:
            index = hourly.index_at(moment)
            if index is None:
                levels.append(0)
                winds.append(0.0)
                continue
            sample = hourly.sample(index)
            levels.append(int(assess(sample, load_lb).level))
            winds.append(round(sample.wind_mph, 1))
        points.append({"lat": point.lat, "lon": point.lon, "levels": levels, "wind_mph": winds})

    return {
        "start": start.isoformat(),
        "hours": [moment.isoformat() for moment in times],
        "points": points,
    }


def corridor_grid(
    routes: Sequence[Sequence[Sequence[float]]],
    bounds: Sequence[Sequence[float]],
    *,
    max_points: int,
    half_width_miles: float = CORRIDOR_HALF_WIDTH_MILES,
) -> list[GeoPoint]:
    """Regular lat/lon grid over the padded bounds, keeping cells near any route."""
    (min_lon, min_lat), (max_lon, max_lat) = bounds
    width = max(max_lon - min_lon, 0.2)
    height = max(max_lat - min_lat, 0.2)
    pad_lon, pad_lat = width * 0.15 + 0.1, height * 0.15 + 0.1
    min_lon, max_lon = min_lon - pad_lon, max_lon + pad_lon
    min_lat, max_lat = min_lat - pad_lat, max_lat + pad_lat

    spacing = max((max_lon - min_lon) / TARGET_COLUMNS, MIN_SPACING_DEG)
    samples = [
        GeoPoint(lat, lon)
        for coords in routes
        for lon, lat in (coords[i] for i in range(0, len(coords), ROUTE_SAMPLE_STEP))
    ] + [GeoPoint(coords[-1][1], coords[-1][0]) for coords in routes if coords]
    half_width_m = miles_to_meters(half_width_miles)

    while True:
        candidates = _grid(min_lon, max_lon, min_lat, max_lat, spacing)
        near = [p for p in candidates if _near_any(p, samples, half_width_m, spacing)]
        if len(near) <= max_points or spacing > 2.0:
            return near[:max_points]
        spacing *= 1.25


def _grid(
    min_lon: float, max_lon: float, min_lat: float, max_lat: float, spacing: float
) -> list[GeoPoint]:
    cols = int(math.ceil((max_lon - min_lon) / spacing)) + 1
    rows = int(math.ceil((max_lat - min_lat) / spacing)) + 1
    return [
        GeoPoint(round(min_lat + r * spacing, 4), round(min_lon + c * spacing, 4))
        for r in range(rows)
        for c in range(cols)
    ]


def _near_any(point: GeoPoint, samples: list[GeoPoint], radius_m: float, spacing: float) -> bool:
    # Cheap bounding-box reject before the haversine.
    deg = radius_m / 111_000 + spacing
    for s in samples:
        if abs(s.lat - point.lat) > deg or abs(s.lon - point.lon) > deg:
            continue
        if point.distance_to(s) <= radius_m + miles_to_meters(spacing * 69 / 2):
            return True
    return False
