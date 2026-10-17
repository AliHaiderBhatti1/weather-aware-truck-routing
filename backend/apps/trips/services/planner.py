"""
Trip planning use-case: the only place that knows about every other domain.

    places  ->  routes  ->  checkpoints  ->  weather  ->  risk  ->  ranking

The result is a plain JSON-serialisable dict so it can be persisted as-is and
returned verbatim by the API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings

from apps.geo.sampling import sample_checkpoints
from apps.geo.service import GeoService
from apps.geo.simplify import simplify
from apps.geo.types import Checkpoint, GeoPoint, Place, Route
from apps.risk.engine import RiskAssessment, WeatherSample, assess
from apps.risk.levels import RiskLevel
from apps.risk.ranking import RiskSegment, rank_routes, summarize_route
from apps.trips.services.timing import StageTimer
from apps.weather.service import WeatherService

logger = logging.getLogger(__name__)

GEOMETRY_TOLERANCE_DEG = 0.0003  # ~30 m: invisible on a map, ~10x fewer vertices


@dataclass(frozen=True, slots=True)
class PlanRequest:
    origin: Place
    destination: Place
    departure: datetime
    load_lb: int
    interval_miles: int


@dataclass(frozen=True, slots=True)
class AssessedCheckpoint:
    checkpoint: Checkpoint
    weather: WeatherSample | None
    risk: RiskAssessment | None


class TripPlanner:
    def __init__(
        self, geo: GeoService | None = None, weather: WeatherService | None = None
    ) -> None:
        self._geo = geo or GeoService()
        self._weather = weather or WeatherService()

    # -- public ----------------------------------------------------------

    def resolve_place(self, data: dict[str, Any]) -> Place:
        if "lat" in data and "lon" in data:
            point = GeoPoint(float(data["lat"]), float(data["lon"]))
            name = data.get("name") or data.get("query") or f"{point.lat:.4f}, {point.lon:.4f}"
            return Place(name=name, full_name=name, point=point)
        return self._geo.resolve(data["query"])

    def plan(self, request: PlanRequest, timer: StageTimer | None = None) -> dict[str, Any]:
        timer = timer or StageTimer()
        with timer.stage("routes"):
            routes = self._geo.route_options(request.origin.point, request.destination.point)

        with timer.stage("checkpoints"):
            checkpoints_by_route = {
                route.id: sample_checkpoints(route, request.interval_miles, request.departure)
                for route in routes
            }
        with timer.stage("weather"):
            assessed = self._assess_all(checkpoints_by_route, request.load_lb)
        with timer.stage("rank"):
            result = self._build_result(request, routes, assessed)
        logger.info(
            "plan %s -> %s: %s", request.origin.name, request.destination.name, timer.summary()
        )
        return result

    def _build_result(
        self,
        request: PlanRequest,
        routes: list[Route],
        assessed: dict[str, list[AssessedCheckpoint]],
    ) -> dict[str, Any]:
        summaries = [
            summarize_route(
                route.id,
                route.duration_s,
                [
                    RiskSegment(item.risk.level, item.checkpoint.segment_miles)
                    for item in assessed[route.id]
                    if item.risk is not None
                ],
            )
            for route in routes
        ]
        ranked = {item.summary.route_id: item for item in rank_routes(summaries)}

        warnings = self._warnings(routes, assessed)
        recommended = next((r for r in ranked.values() if r.recommended), None)
        if recommended is None:
            warnings.append(
                "Every route contains No-Travel conditions at the planned departure time. "
                "Consider delaying the trip."
            )

        route_payloads = sorted(
            (
                _serialize_route(route, ranked[route.id], assessed[route.id], request.departure)
                for route in routes
            ),
            key=lambda payload: payload["rank"],
        )

        return {
            "request": {
                "origin": _serialize_place(request.origin),
                "destination": _serialize_place(request.destination),
                "departure_time": request.departure.isoformat(),
                "load_weight_lb": request.load_lb,
                "checkpoint_interval_miles": request.interval_miles,
            },
            "recommended_route_id": recommended.summary.route_id if recommended else None,
            "recommendation_reasons": recommended.reasons if recommended else [],
            "warnings": warnings,
            "routes": route_payloads,
            "bounds": _bounds(routes),
            "forecast_window": {
                "start": _floor_hour(request.departure).isoformat(),
                "end": (
                    _floor_hour(request.departure)
                    + timedelta(hours=settings.HEATMAP_FORECAST_HOURS)
                ).isoformat(),
                "hours": settings.HEATMAP_FORECAST_HOURS,
            },
        }

    # -- internals -------------------------------------------------------

    def _assess_all(
        self, checkpoints_by_route: dict[str, list[Checkpoint]], load_lb: int
    ) -> dict[str, list[AssessedCheckpoint]]:
        """One batched weather call for every checkpoint of every route."""
        flat: list[tuple[str, Checkpoint]] = [
            (route_id, checkpoint)
            for route_id, checkpoints in checkpoints_by_route.items()
            for checkpoint in checkpoints
        ]
        samples = self._weather.samples_at([(cp.point, cp.eta) for _, cp in flat])

        assessed: dict[str, list[AssessedCheckpoint]] = {rid: [] for rid in checkpoints_by_route}
        for (route_id, checkpoint), sample in zip(flat, samples, strict=True):
            risk = assess(sample, load_lb) if sample is not None else None
            assessed[route_id].append(AssessedCheckpoint(checkpoint, sample, risk))
        return assessed

    @staticmethod
    def _warnings(routes: list[Route], assessed: dict[str, list[AssessedCheckpoint]]) -> list[str]:
        warnings: list[str] = []
        if len(routes) < 3:
            count = len(routes)
            warnings.append(
                f"Only {count} distinct route{'s exist' if count != 1 else ' exists'} "
                "between these places."
            )
        missing = sum(1 for items in assessed.values() for item in items if item.weather is None)
        if missing:
            warnings.append(
                f"Forecast data was unavailable for {missing} checkpoint(s); "
                "they are excluded from risk totals."
            )
        return warnings


# -- serialisation helpers ---------------------------------------------------


def _serialize_place(place: Place) -> dict[str, Any]:
    return {
        "name": place.name,
        "full_name": place.full_name,
        "lat": place.point.lat,
        "lon": place.point.lon,
    }


def _serialize_route(
    route: Route,
    ranked: Any,
    assessed: list[AssessedCheckpoint],
    departure: datetime,
) -> dict[str, Any]:
    summary = ranked.summary
    return {
        "id": route.id,
        "name": route.name,
        "source": route.source,
        "rank": ranked.rank,
        "recommended": ranked.recommended,
        "distance_miles": round(route.distance_miles, 1),
        "duration_seconds": round(route.duration_s),
        "arrival_time": (departure + timedelta(seconds=route.duration_s)).isoformat(),
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [round(lon, 5), round(lat, 5)]
                for lon, lat in simplify(route.coordinates, GEOMETRY_TOLERANCE_DEG)
            ],
        },
        "summary": {
            "max_level": summary.max_level.slug,
            "average_risk": round(summary.average_risk, 2),
            "travel_advised": summary.is_travel_advised,
            "no_travel_miles": round(summary.no_travel_miles, 1),
            "severe_miles": round(summary.severe_miles, 1),
            "high_miles": round(summary.high_miles, 1),
            "miles_by_level": {
                level.slug: round(miles, 1) for level, miles in summary.miles_by_level.items()
            },
        },
        "checkpoints": [_serialize_checkpoint(item) for item in assessed],
    }


def _serialize_checkpoint(item: AssessedCheckpoint) -> dict[str, Any]:
    cp, weather, risk = item.checkpoint, item.weather, item.risk
    return {
        "index": cp.index,
        "lat": round(cp.point.lat, 5),
        "lon": round(cp.point.lon, 5),
        "distance_from_start_miles": round(cp.distance_from_start_miles, 1),
        "segment_miles": round(cp.segment_miles, 1),
        "eta": cp.eta.isoformat(),
        "weather": None
        if weather is None
        else {
            "wind_mph": round(weather.wind_mph, 1),
            "wind_gust_mph": None
            if weather.wind_gust_mph is None
            else round(weather.wind_gust_mph, 1),
            "rain_in_per_hr": round(weather.rain_in_per_hr, 3),
            "snow_in_per_hr": round(weather.snow_in_per_hr, 3),
            "temperature_f": None
            if weather.temperature_f is None
            else round(weather.temperature_f),
            "weather_code": weather.weather_code,
        },
        "risk": None
        if risk is None
        else {
            "level": risk.level.slug,
            "label": risk.level.label,
            "score": int(risk.level),
            "wind_level": risk.wind_level.slug,
            "rain_level": risk.rain_level.slug,
            "snow_level": risk.snow_level.slug,
            "dominant_factor": str(risk.dominant_factor),
            "applied_rule": risk.applied_rule,
        },
    }


def _bounds(routes: list[Route]) -> list[list[float]]:
    lons = [lon for route in routes for lon, _ in route.coordinates]
    lats = [lat for route in routes for _, lat in route.coordinates]
    return [
        [round(min(lons), 5), round(min(lats), 5)],
        [round(max(lons), 5), round(max(lats), 5)],
    ]


def _floor_hour(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


__all__ = ["PlanRequest", "RiskLevel", "TripPlanner"]
