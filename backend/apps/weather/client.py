"""
Open-Meteo forecast client.

Open-Meteo accepts comma separated latitude/longitude lists, so all checkpoints
of all routes (or a whole heatmap grid) can be fetched in a handful of calls.
Units are requested in the brief's vocabulary (mph, inches, Fahrenheit) so no
conversion happens downstream.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import httpx
from django.conf import settings

from apps.geo.types import GeoPoint
from apps.trips.exceptions import RateLimitedError, UpstreamError
from apps.weather.types import HourlySeries

logger = logging.getLogger(__name__)

HOURLY_FIELDS = (
    "wind_speed_10m",
    "wind_gusts_10m",
    "rain",
    "showers",
    "snowfall",
    "temperature_2m",
    "weather_code",
)
# Open-Meteo's latency grows with locations per call, but its free tier is
# rate-limited per *request*, so fewer, larger calls are the better trade.
MAX_LOCATIONS_PER_REQUEST = 40
MAX_CONCURRENT_REQUESTS = 4
RETRIES_ON_TIMEOUT = 1
RETRY_AFTER_RATE_LIMIT_SECONDS = 3.0


class OpenMeteoClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        http: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url or settings.OPEN_METEO_BASE_URL
        self._http = http or httpx.Client(timeout=timeout or settings.OPEN_METEO_TIMEOUT_SECONDS)

    def hourly(
        self, points: Sequence[GeoPoint], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        """
        Hourly series for every point between ``start`` and ``end`` (inclusive hours, UTC).

        Points are split into small chunks fetched concurrently: Open-Meteo's
        latency grows roughly linearly with the number of locations per call.
        """
        if not points:
            return []
        chunks = [
            points[offset : offset + MAX_LOCATIONS_PER_REQUEST]
            for offset in range(0, len(points), MAX_LOCATIONS_PER_REQUEST)
        ]
        if len(chunks) == 1:
            return self._fetch_chunk_with_retry(chunks[0], start, end)
        workers = min(MAX_CONCURRENT_REQUESTS, len(chunks))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(
                pool.map(lambda chunk: self._fetch_chunk_with_retry(chunk, start, end), chunks)
            )
        return [series for chunk_series in results for series in chunk_series]

    def _fetch_chunk_with_retry(
        self, points: Sequence[GeoPoint], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        attempt = 0
        while True:
            try:
                return self._fetch_chunk(points, start, end)
            except RateLimitedError:
                attempt += 1
                if attempt > RETRIES_ON_TIMEOUT:
                    raise
                logger.info("Open-Meteo rate limited; retrying chunk after a short pause")
                time.sleep(RETRY_AFTER_RATE_LIMIT_SECONDS)
            except UpstreamError as exc:
                attempt += 1
                if attempt > RETRIES_ON_TIMEOUT or "Timeout" not in exc.message:
                    raise
                logger.info("Open-Meteo timed out; retrying chunk of %d points", len(points))

    def _fetch_chunk(
        self, points: Sequence[GeoPoint], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        params = {
            "latitude": ",".join(f"{p.lat:.4f}" for p in points),
            "longitude": ",".join(f"{p.lon:.4f}" for p in points),
            "hourly": ",".join(HOURLY_FIELDS),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "temperature_unit": "fahrenheit",
            "timezone": "UTC",
            "start_hour": _format_hour(start),
            "end_hour": _format_hour(end),
        }
        try:
            response = self._http.get(self._base_url, params=params)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Open-Meteo request failed: {exc.__class__.__name__}") from exc

        payload = _safe_json(response)
        if response.status_code == 429:
            logger.warning("Open-Meteo rate limit hit")
            raise RateLimitedError(
                "The weather service is busy right now. Please try again in a minute.",
                details={"provider": "open-meteo"},
            )
        if response.status_code >= 400:
            reason = payload.get("reason") if isinstance(payload, dict) else None
            logger.warning("Open-Meteo -> %s %s", response.status_code, reason)
            raise UpstreamError(
                f"Open-Meteo returned HTTP {response.status_code}",
                details={"reason": reason} if reason else None,
            )

        # One location -> object; many -> list of objects.
        entries = payload if isinstance(payload, list) else [payload]
        if len(entries) != len(points):
            raise UpstreamError(
                "Open-Meteo returned an unexpected number of locations",
                details={"expected": len(points), "received": len(entries)},
            )
        return [_parse_series(point, entry) for point, entry in zip(points, entries, strict=True)]


def _parse_series(point: GeoPoint, entry: Any) -> HourlySeries:
    hourly = entry.get("hourly", {}) if isinstance(entry, dict) else {}
    times = [_parse_time(value) for value in hourly.get("time", [])]
    count = len(times)

    def floats(name: str) -> list[float]:
        values = hourly.get(name) or []
        return [float(v) if v is not None else 0.0 for v in values][:count] + [0.0] * max(
            0, count - len(values)
        )

    rain = [a + b for a, b in zip(floats("rain"), floats("showers"), strict=True)]
    codes = hourly.get("weather_code") or []
    return HourlySeries(
        point=point,
        times=times,
        wind_mph=floats("wind_speed_10m"),
        wind_gust_mph=floats("wind_gusts_10m"),
        rain_in=rain,
        snow_in=floats("snowfall"),
        temperature_f=floats("temperature_2m"),
        weather_code=[int(c) if c is not None else 0 for c in codes][:count]
        + [0] * max(0, count - len(codes)),
    )


def _format_hour(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:00")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
