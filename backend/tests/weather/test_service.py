from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from django.core.cache import cache

from apps.geo.types import GeoPoint
from apps.weather.service import WeatherService
from apps.weather.types import HourlySeries

T0 = datetime(2026, 10, 20, 8, tzinfo=UTC)


def _series(point: GeoPoint, hours: int = 3, wind: float = 10.0) -> HourlySeries:
    return HourlySeries(
        point=point,
        times=[T0 + timedelta(hours=i) for i in range(hours)],
        wind_mph=[wind + i for i in range(hours)],
        wind_gust_mph=[wind + 5 for _ in range(hours)],
        rain_in=[0.0] * hours,
        snow_in=[0.0] * hours,
        temperature_f=[50.0] * hours,
        weather_code=[0] * hours,
    )


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[int, datetime, datetime]] = []
        self.chunk_sizes: list[int] = []

    def hourly(self, points, start, end, *, chunk_size=40):  # type: ignore[no-untyped-def]
        self.calls.append((len(points), start, end))
        self.chunk_sizes.append(chunk_size)
        return [_series(p) for p in points]


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


def test_sample_at_uses_the_hour_bucket_containing_the_time() -> None:
    series = _series(GeoPoint(0, 0))

    assert series.sample_at(T0 + timedelta(minutes=59)).wind_mph == 10.0  # type: ignore[union-attr]
    assert series.sample_at(T0 + timedelta(hours=1)).wind_mph == 11.0  # type: ignore[union-attr]
    assert series.sample_at(T0 + timedelta(hours=2, minutes=59)).wind_mph == 12.0  # type: ignore[union-attr]


def test_sample_at_outside_range_is_none() -> None:
    series = _series(GeoPoint(0, 0))
    assert series.sample_at(T0 - timedelta(minutes=1)) is None
    assert series.sample_at(T0 + timedelta(hours=3)) is None


def test_samples_at_fetches_one_window_for_all_points() -> None:
    client = FakeClient()
    service = WeatherService(client=client)  # type: ignore[arg-type]
    requests = [
        (GeoPoint(1, 1), T0 + timedelta(minutes=10)),
        (GeoPoint(2, 2), T0 + timedelta(hours=2, minutes=30)),
    ]

    samples = service.samples_at(requests)

    assert client.calls == [(2, T0, T0 + timedelta(hours=2))]
    assert client.chunk_sizes == [12]  # latency-critical path uses small chunks
    assert [s.wind_mph for s in samples if s] == [10.0, 12.0]


def test_hourly_results_are_cached_per_point_and_window() -> None:
    client = FakeClient()
    service = WeatherService(client=client)  # type: ignore[arg-type]
    points = [GeoPoint(1, 1), GeoPoint(2, 2)]

    service.hourly(points, T0, T0 + timedelta(hours=2))
    service.hourly([*points, GeoPoint(3, 3)], T0 + timedelta(minutes=20), T0 + timedelta(hours=2))

    # Second call only fetches the new point; the window floors to the same hours.
    assert client.calls == [(2, T0, T0 + timedelta(hours=2)), (1, T0, T0 + timedelta(hours=2))]


def test_end_before_start_is_clamped() -> None:
    client = FakeClient()
    WeatherService(client=client).hourly([GeoPoint(1, 1)], T0 + timedelta(hours=1), T0)  # type: ignore[arg-type]
    assert client.calls[0][1] == client.calls[0][2]


def test_duplicate_points_are_fetched_once_but_returned_for_each_request() -> None:
    client = FakeClient()
    service = WeatherService(client=client)  # type: ignore[arg-type]
    shared = GeoPoint(1.0, 1.0)

    series = service.hourly([shared, GeoPoint(2, 2), shared, GeoPoint(1.001, 1.001)], T0, T0)

    assert client.calls == [(2, T0, T0)]  # shared + 1.001 round to the same ~1 km key
    assert len(series) == 4
    assert series[0] is series[2]


def test_window_is_clamped_to_the_forecast_horizon(settings: object) -> None:
    settings.FORECAST_HORIZON_DAYS = 15  # type: ignore[attr-defined]
    client = FakeClient()
    far_start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(days=14)
    far_end = far_start + timedelta(days=4)

    WeatherService(client=client).hourly([GeoPoint(1, 1)], far_start, far_end)  # type: ignore[arg-type]

    _, start, end = client.calls[0]
    assert start == far_start
    assert end <= datetime.now(UTC) + timedelta(days=15)
    assert end >= start
