"""Hourly forecast series for one location."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta

from apps.geo.types import GeoPoint
from apps.risk.engine import WeatherSample


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """
    Hourly forecast for ``point``. ``times`` are UTC bucket starts; every other
    list is aligned with it. Precipitation values are the hour's accumulated
    totals, which equals the in/hr rate the risk rules expect.
    """

    point: GeoPoint
    times: list[datetime]
    wind_mph: list[float]
    wind_gust_mph: list[float]
    rain_in: list[float]
    snow_in: list[float]
    temperature_f: list[float]
    weather_code: list[int]

    def index_at(self, when: datetime) -> int | None:
        """Index of the hour bucket that contains ``when``, or ``None`` if out of range."""
        if not self.times:
            return None
        position = bisect_right(self.times, when) - 1
        if position < 0:
            return None
        if when - self.times[position] >= timedelta(hours=1):
            return None
        return position

    def sample_at(self, when: datetime) -> WeatherSample | None:
        index = self.index_at(when)
        if index is None:
            return None
        return self.sample(index)

    def sample(self, index: int) -> WeatherSample:
        return WeatherSample(
            wind_mph=self.wind_mph[index],
            rain_in_per_hr=self.rain_in[index],
            snow_in_per_hr=self.snow_in[index],
            wind_gust_mph=self.wind_gust_mph[index],
            temperature_f=self.temperature_f[index],
            weather_code=self.weather_code[index],
        )
