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
from apps.trips.exceptions import RateLimitedError, TransientUpstreamError, UpstreamError
from apps.weather.types import HourlySeries

logger = logging.getLogger(__name__)

# Open-Meteo weights its rate limit by locations x variables x days, so the
# background heatmap asks only for what the risk rules need.
HOURLY_FIELDS = (
    "wind_speed_10m",
    "wind_gusts_10m",
    "rain",
    "showers",
    "snowfall",
    "temperature_2m",
    "weather_code",
)
RISK_ONLY_FIELDS = ("wind_speed_10m", "rain", "showers", "snowfall")
# Open-Meteo's latency grows roughly linearly with locations per call, while
# its free tier is rate-limited per *request*. Latency-critical calls (the
# checkpoints of a plan) use small concurrent chunks; background work (the
# heatmap grid) uses large ones to stay well inside the request budget.
DEFAULT_CHUNK_SIZE = 40
FAST_CHUNK_SIZE = 12
MAX_CONCURRENT_REQUESTS = 6
# Transient failures (timeouts, 429/5xx, malformed answers) are retried with a
# linear backoff: 1.5 s, then 3 s.
TRANSIENT_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.5
BUSY_MESSAGE = "The weather service is busy right now. Please try again in a minute."


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
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        fields: Sequence[str] = HOURLY_FIELDS,
    ) -> list[HourlySeries]:
        """
        Hourly series for every point between ``start`` and ``end`` (inclusive hours, UTC).

        Points are split into ``chunk_size`` groups fetched concurrently.
        """
        if not points:
            return []
        chunk_size = max(1, chunk_size)
        chunks = [
            points[offset : offset + chunk_size] for offset in range(0, len(points), chunk_size)
        ]
        if len(chunks) == 1:
            return self._fetch_chunk_with_retry(chunks[0], start, end, fields)
        workers = min(MAX_CONCURRENT_REQUESTS, len(chunks))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(
                pool.map(
                    lambda chunk: self._fetch_chunk_with_retry(chunk, start, end, fields), chunks
                )
            )
        return [series for chunk_series in results for series in chunk_series]

    def _fetch_chunk_with_retry(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
        fields: Sequence[str] = HOURLY_FIELDS,
    ) -> list[HourlySeries]:
        attempt = 0
        while True:
            try:
                return self._fetch_chunk(points, start, end, fields)
            except TransientUpstreamError as exc:
                attempt += 1
                if attempt > TRANSIENT_RETRIES:
                    raise
                logger.info(
                    "Open-Meteo transient failure (%s); retry %d for %d points",
                    exc.details or exc.message,
                    attempt,
                    len(points),
                )
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    def _fetch_chunk(
        self,
        points: Sequence[GeoPoint],
        start: datetime,
        end: datetime,
        fields: Sequence[str] = HOURLY_FIELDS,
    ) -> list[HourlySeries]:
        params = {
            "latitude": ",".join(f"{p.lat:.4f}" for p in points),
            "longitude": ",".join(f"{p.lon:.4f}" for p in points),
            "hourly": ",".join(fields),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "temperature_unit": "fahrenheit",
            "timezone": "UTC",
            "start_hour": _format_hour(start),
            "end_hour": _format_hour(end),
        }
        try:
            response = self._http.get(self._base_url, params=params)
        except httpx.TransportError as exc:  # timeouts, connection resets, DNS
            raise TransientUpstreamError(
                BUSY_MESSAGE, details={"provider": "open-meteo", "cause": type(exc).__name__}
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Open-Meteo request failed: {exc.__class__.__name__}") from exc

        payload = _safe_json(response)
        reason = payload.get("reason") if isinstance(payload, dict) else None
        if response.status_code == 429:
            logger.warning("Open-Meteo rate limit: %s", reason)
            raise RateLimitedError(BUSY_MESSAGE, details={"provider": "open-meteo", "status": 429})
        if response.status_code >= 500:
            logger.warning("Open-Meteo %s: %s", response.status_code, reason)
            raise TransientUpstreamError(
                BUSY_MESSAGE, details={"provider": "open-meteo", "status": response.status_code}
            )
        if response.status_code >= 400:
            logger.warning("Open-Meteo -> %s %s", response.status_code, reason)
            raise UpstreamError(
                f"Open-Meteo returned HTTP {response.status_code}",
                details={"reason": reason} if reason else None,
            )

        # One location -> object; many -> list of objects. Under load the API
        # occasionally answers a multi-location request with a single object,
        # so a count mismatch is treated as transient and retried.
        entries = payload if isinstance(payload, list) else [payload]
        if len(entries) != len(points) or not all(isinstance(e, dict) for e in entries):
            logger.warning(
                "Open-Meteo malformed answer: expected %d locations, got %s (reason=%s)",
                len(points),
                f"list of {len(entries)}" if isinstance(payload, list) else type(payload).__name__,
                reason,
            )
            raise TransientUpstreamError(
                BUSY_MESSAGE,
                details={
                    "provider": "open-meteo",
                    "expected": len(points),
                    "received": len(entries),
                },
            )
        return [_parse_series(point, entry) for point, entry in zip(points, entries, strict=True)]


def _parse_series(point: GeoPoint, entry: Any) -> HourlySeries:
    hourly = entry.get("hourly", {}) if isinstance(entry, dict) else {}
    times = [_parse_time(value) for value in hourly.get("time", [])]
    count = len(times)

    def values(name: str) -> list[float | None]:
        # Missing values stay None: a gap in the forecast is unknown, not calm.
        raw = list(hourly.get(name) or [])[:count]
        raw += [None] * (count - len(raw))
        return [float(v) if v is not None else None for v in raw]

    rain = [_add_present(a, b) for a, b in zip(values("rain"), values("showers"), strict=True)]
    codes = values("weather_code")
    return HourlySeries(
        point=point,
        times=times,
        wind_mph=values("wind_speed_10m"),
        wind_gust_mph=values("wind_gusts_10m"),
        rain_in=rain,
        snow_in=values("snowfall"),
        temperature_f=values("temperature_2m"),
        weather_code=[int(c) if c is not None else None for c in codes],
    )


def _add_present(a: float | None, b: float | None) -> float | None:
    """Sum of the values that are present; None only when both are missing."""
    if a is None and b is None:
        return None
    return (a or 0.0) + (b or 0.0)


def _format_hour(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:00")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
