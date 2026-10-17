"""Hourly forecast series for one location."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from apps.geo.types import GeoPoint
from apps.risk.engine import WeatherSample

HOUR = timedelta(hours=1)
HALF_HOUR = timedelta(minutes=30)


def floor_hour(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """
    Hourly forecast for ``point`` with every list aligned to ``times`` (UTC).

    Open-Meteo stamps two kinds of values differently:

    * accumulations and maxima (``rain``, ``showers``, ``snowfall``, gusts,
      weather code) cover the *preceding* hour, so the value stamped 03:00 is
      the total for 02:00-03:00, which is the in/hr rate the risk rules expect;
    * instantaneous values (wind speed, temperature) are readings at the stamp.
    """

    point: GeoPoint
    times: list[datetime]
    wind_mph: list[float | None]
    wind_gust_mph: list[float | None]
    rain_in: list[float | None]
    snow_in: list[float | None]
    temperature_f: list[float | None]
    weather_code: list[int | None]

    def _index_of(self, stamp: datetime) -> int | None:
        if not self.times:
            return None
        offset = stamp - self.times[0]
        index, remainder = divmod(offset, HOUR)
        if remainder or not 0 <= index < len(self.times):
            return None
        return int(index)

    def sample_at(self, when: datetime) -> WeatherSample | None:
        """
        Weather for a truck passing at ``when``.

        Precipitation and gusts come from the hour that contains ``when`` (the
        value stamped at the end of that hour); wind and temperature from the
        nearest reading. Returns ``None`` when either is outside the series or
        any value the risk rules need (wind, rain, snow) is missing.
        """
        hour_start = floor_hour(when)
        hour_index = self._index_of(hour_start + HOUR)
        nearest = hour_start if when - hour_start < HALF_HOUR else hour_start + HOUR
        reading_index = self._index_of(nearest)
        if hour_index is None or reading_index is None:
            return None
        wind = self.wind_mph[reading_index]
        rain = self.rain_in[hour_index]
        snow = self.snow_in[hour_index]
        if wind is None or rain is None or snow is None:
            return None
        return WeatherSample(
            wind_mph=wind,
            rain_in_per_hr=rain,
            snow_in_per_hr=snow,
            wind_gust_mph=self.wind_gust_mph[hour_index],
            temperature_f=self.temperature_f[reading_index],
            weather_code=self.weather_code[hour_index],
        )
