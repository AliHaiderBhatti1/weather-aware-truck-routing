"""Checkpoint sampling: walk a route and emit a point every N miles with its ETA."""

from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timedelta
from itertools import accumulate

from apps.geo.types import Checkpoint, GeoPoint, Route
from apps.geo.units import meters_to_miles, miles_to_meters


def sample_checkpoints(
    route: Route, interval_miles: float, departure: datetime
) -> list[Checkpoint]:
    """
    Return checkpoints at 0, N, 2N ... miles plus the destination.

    Positions and elapsed times are interpolated linearly inside the route
    segment that contains each target distance, using the provider's per-segment
    distance and duration annotations. The final checkpoint is always the
    destination; a trailing stub shorter than 10% of the interval is merged
    into it so we don't sample twice within a mile or two.
    """
    if interval_miles <= 0:
        raise ValueError("interval_miles must be positive")

    cum_dist = [0.0, *accumulate(route.segment_distances_m)]
    cum_time = [0.0, *accumulate(route.segment_durations_s)]
    total_m = cum_dist[-1]
    step_m = miles_to_meters(interval_miles)

    targets: list[float] = []
    distance = 0.0
    while distance < total_m:
        targets.append(distance)
        distance += step_m
    if targets and total_m - targets[-1] < step_m * 0.1 and len(targets) > 1:
        targets.pop()
    targets.append(total_m)

    checkpoints: list[Checkpoint] = []
    for index, target in enumerate(targets):
        point, elapsed = _locate(route, cum_dist, cum_time, target)
        checkpoints.append(
            Checkpoint(
                index=index,
                point=point,
                distance_from_start_miles=meters_to_miles(target),
                elapsed_seconds=elapsed,
                eta=departure + timedelta(seconds=elapsed),
            )
        )

    return [
        Checkpoint(
            index=cp.index,
            point=cp.point,
            distance_from_start_miles=cp.distance_from_start_miles,
            elapsed_seconds=cp.elapsed_seconds,
            eta=cp.eta,
            segment_miles=(
                checkpoints[i + 1].distance_from_start_miles - cp.distance_from_start_miles
                if i + 1 < len(checkpoints)
                else 0.0
            ),
        )
        for i, cp in enumerate(checkpoints)
    ]


def _locate(
    route: Route, cum_dist: list[float], cum_time: list[float], target_m: float
) -> tuple[GeoPoint, float]:
    """Interpolate the coordinate and elapsed seconds at ``target_m`` along the route."""
    if target_m <= 0:
        lon, lat = route.coordinates[0]
        return GeoPoint(lat, lon), 0.0
    if target_m >= cum_dist[-1]:
        lon, lat = route.coordinates[-1]
        return GeoPoint(lat, lon), cum_time[-1]

    seg = bisect_right(cum_dist, target_m) - 1
    seg = min(max(seg, 0), len(route.coordinates) - 2)
    seg_len = cum_dist[seg + 1] - cum_dist[seg]
    fraction = (target_m - cum_dist[seg]) / seg_len if seg_len > 0 else 0.0

    lon0, lat0 = route.coordinates[seg]
    lon1, lat1 = route.coordinates[seg + 1]
    point = GeoPoint(lat0 + (lat1 - lat0) * fraction, lon0 + (lon1 - lon0) * fraction)
    elapsed = cum_time[seg] + (cum_time[seg + 1] - cum_time[seg]) * fraction
    return point, elapsed


def densify(route: Route, every_miles: float) -> list[GeoPoint]:
    """Evenly spaced points along the route (used for overlap tests and corridors)."""
    cum_dist = [0.0, *accumulate(route.segment_distances_m)]
    cum_time = [0.0, *accumulate(route.segment_durations_s)]
    step = miles_to_meters(every_miles)
    points: list[GeoPoint] = []
    distance = 0.0
    while distance <= cum_dist[-1]:
        points.append(_locate(route, cum_dist, cum_time, distance)[0])
        distance += step
    return points
