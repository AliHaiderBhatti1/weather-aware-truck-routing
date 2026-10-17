"""Weather use-cases built on the Open-Meteo client, with caching."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, overload

from django.conf import settings
from django.core.cache import cache

from apps.geo.types import GeoPoint
from apps.risk.engine import WeatherSample
from apps.weather.client import (
    DEFAULT_CHUNK_SIZE,
    FAST_CHUNK_SIZE,
    HOURLY_FIELDS,
    OpenMeteoClient,
)
from apps.weather.types import HOUR, HourlySeries


@dataclass(frozen=True, slots=True)
class ForecastBatch:
    samples: list[WeatherSample | None]
    """One entry per request; ``None`` when no forecast is available."""
    unavailable: int
    """How many requests got nothing because the provider failed (vs. out of range)."""


class WeatherService:
    def __init__(self, client: OpenMeteoClient | None = None) -> None:
        self._client = client or OpenMeteoClient()

    @overload
    def hourly(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
        *,
        chunk_size: int = ...,
        fields: Sequence[str] = ...,
        allow_partial: Literal[False] = ...,
    ) -> list[HourlySeries]: ...

    @overload
    def hourly(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
        *,
        chunk_size: int = ...,
        fields: Sequence[str] = ...,
        allow_partial: Literal[True],
    ) -> list[HourlySeries | None]: ...

    @overload
    def hourly(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
        *,
        chunk_size: int = ...,
        fields: Sequence[str] = ...,
        allow_partial: bool = ...,
    ) -> list[HourlySeries | None]: ...

    def hourly(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        fields: Sequence[str] = HOURLY_FIELDS,
        allow_partial: bool = False,
    ) -> list[HourlySeries] | list[HourlySeries | None]:
        """
        Hourly series for each point, served from cache when possible.

        With ``allow_partial``, points the provider failed to return are ``None``
        (and are not cached, so the next call retries them).
        """
        start = _floor_hour(start)
        end = _floor_hour(end)
        # Open-Meteo rejects windows past its forecast horizon; clamp and let
        # callers treat the missing hours as "no forecast".
        horizon = _floor_hour(datetime.now(UTC) + timedelta(days=settings.FORECAST_HORIZON_DAYS))
        end = min(end, horizon)
        start = min(start, end)
        end = max(end, start)

        keys = [_cache_key(point, start, end, fields) for point in points]
        cached = cache.get_many(keys)
        # Routes share endpoints and often long stretches, so de-duplicate by
        # cache key (coordinates rounded to ~1 km) before calling upstream.
        missing: dict[str, GeoPoint] = {}
        for key, point in zip(keys, points, strict=True):
            if key not in cached and key not in missing:
                missing[key] = point

        if missing:
            fetched = self._client.hourly(
                list(missing.values()),
                start,
                end,
                chunk_size=chunk_size,
                fields=fields,
                allow_partial=allow_partial,
            )
            fresh = dict(zip(missing.keys(), fetched, strict=True))
            cache.set_many(
                {key: series for key, series in fresh.items() if series is not None},
                settings.WEATHER_CACHE_TTL,
            )
            cached.update(fresh)

        return [cached[key] for key in keys]

    def samples_at(self, requests: Sequence[tuple[GeoPoint, datetime]]) -> ForecastBatch:
        """Weather at each (point, time) pair, fetched in one window; tolerates provider gaps."""
        if not requests:
            return ForecastBatch(samples=[], unavailable=0)
        times = [when for _, when in requests]
        # +1 h: precipitation for the hour containing an ETA is stamped at its end.
        series = self.hourly(
            [point for point, _ in requests],
            min(times),
            max(times) + HOUR,
            chunk_size=FAST_CHUNK_SIZE,
            allow_partial=True,
        )
        samples = [
            hourly.sample_at(when) if hourly is not None else None
            for hourly, (_, when) in zip(series, requests, strict=True)
        ]
        return ForecastBatch(samples=samples, unavailable=sum(1 for h in series if h is None))


def _floor_hour(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _cache_key(point: GeoPoint, start: datetime, end: datetime, fields: Sequence[str]) -> str:
    raw = (
        f"{point.lat:.2f}|{point.lon:.2f}|{start.isoformat()}|{end.isoformat()}|{','.join(fields)}"
    )
    return "weather:" + hashlib.sha1(raw.encode()).hexdigest()[:24]
