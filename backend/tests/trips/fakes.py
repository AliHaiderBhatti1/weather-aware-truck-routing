"""Fakes shared by trip tests: a deterministic weather service and geo service."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

from apps.geo.types import GeoPoint, Place, Route
from apps.risk.engine import WeatherSample
from apps.weather.types import HourlySeries


class FakeWeather:
    """Weather chosen by a callback on (point, time) so tests can shape risk per route."""

    def __init__(self, rule: Callable[[GeoPoint, datetime], WeatherSample | None]) -> None:
        self.rule = rule
        self.sample_calls = 0

    def samples_at(
        self, requests: Sequence[tuple[GeoPoint, datetime]]
    ) -> list[WeatherSample | None]:
        self.sample_calls += 1
        return [self.rule(point, when) for point, when in requests]

    def hourly(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
        *,
        chunk_size: int = 40,
        fields: Sequence[str] | None = None,
    ) -> list[HourlySeries]:
        hours = int((end - start).total_seconds() // 3600) + 1
        series = []
        for point in points:
            samples = [self.rule(point, start + timedelta(hours=i)) for i in range(hours)]
            series.append(
                HourlySeries(
                    point=point,
                    times=[start + timedelta(hours=i) for i in range(hours)],
                    wind_mph=[s.wind_mph if s else 0.0 for s in samples],
                    wind_gust_mph=[0.0] * hours,
                    rain_in=[s.rain_in_per_hr if s else 0.0 for s in samples],
                    snow_in=[s.snow_in_per_hr if s else 0.0 for s in samples],
                    temperature_f=[50.0] * hours,
                    weather_code=[0] * hours,
                )
            )
        return series


class FakeGeo:
    def __init__(self, routes: list[Route], places: dict[str, Place] | None = None) -> None:
        self.routes = routes
        self.places = places or {}

    def resolve(self, query: str) -> Place:
        return self.places[query]

    def route_options(self, origin: GeoPoint, destination: GeoPoint) -> list[Route]:
        return self.routes


def calm(_: GeoPoint, __: datetime) -> WeatherSample:
    return WeatherSample(
        wind_mph=5, rain_in_per_hr=0, snow_in_per_hr=0, wind_gust_mph=8, temperature_f=60
    )
