from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from apps.geo.types import GeoPoint
from apps.trips.exceptions import RateLimitedError, TransientUpstreamError, UpstreamError
from apps.weather import client as client_module
from apps.weather.client import OpenMeteoClient

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
URL = "https://meteo.test/v1/forecast"
START = datetime(2026, 10, 20, 8, 15, tzinfo=UTC)
END = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
POINTS = [GeoPoint(39.75, -105.0), GeoPoint(40.0, -106.0)]


def _client() -> OpenMeteoClient:
    return OpenMeteoClient(base_url=URL, timeout=5)


@respx.mock
def test_multi_location_request_and_parsing() -> None:
    route = respx.get(URL).mock(
        return_value=httpx.Response(
            200, json=json.loads((FIXTURES / "open_meteo_multi.json").read_text())
        )
    )

    series = _client().hourly(POINTS, START, END)

    params = route.calls.last.request.url.params
    assert params["latitude"] == "39.7500,40.0000"
    assert params["longitude"] == "-105.0000,-106.0000"
    assert params["wind_speed_unit"] == "mph"
    assert params["precipitation_unit"] == "inch"
    assert params["timezone"] == "UTC"
    assert params["start_hour"] == "2026-10-20T08:00"
    assert params["end_hour"] == "2026-10-20T10:00"

    assert len(series) == 2
    first = series[0]
    assert first.point == POINTS[0]
    assert first.times[0] == datetime(2026, 10, 20, 8, tzinfo=UTC)
    assert first.rain_in == [0.0, pytest.approx(0.3), 0.0]  # rain + showers, null -> 0
    assert first.wind_mph == [10.0, 30.0, 58.0]
    assert first.weather_code == [0, 61, 75]


@respx.mock
def test_single_location_object_response_is_accepted() -> None:
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())[0]
    respx.get(URL).mock(return_value=httpx.Response(200, json=body))

    series = _client().hourly([POINTS[0]], START, END)

    assert len(series) == 1
    assert series[0].snow_in[2] == 2.5


@respx.mock
def test_requests_are_chunked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "MAX_CONCURRENT_REQUESTS", 1)
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(200, json=body),
            httpx.Response(200, json=body[0]),
        ]
    )

    series = _client().hourly([*POINTS, GeoPoint(41.0, -107.0)], START, END, chunk_size=2)

    assert route.call_count == 2
    assert len(series) == 3


@respx.mock
def test_error_responses_become_upstream_errors() -> None:
    respx.get(URL).mock(return_value=httpx.Response(400, json={"reason": "Invalid coordinates"}))
    with pytest.raises(UpstreamError) as info:
        _client().hourly(POINTS, START, END)
    assert info.value.details == {"reason": "Invalid coordinates"}


@pytest.fixture
def no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "RETRY_BACKOFF_SECONDS", 0)


@respx.mock
def test_location_count_mismatch_is_retried_then_reported_as_busy(no_backoff: None) -> None:
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=body[0]))  # 1 of 2

    with pytest.raises(TransientUpstreamError) as info:
        _client().hourly(POINTS, START, END)

    assert route.call_count == 3  # initial attempt + 2 retries
    assert info.value.code == "provider_busy"
    assert info.value.http_status == 503
    assert info.value.details["expected"] == 2


@respx.mock
def test_location_count_mismatch_then_success_recovers(no_backoff: None) -> None:
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    respx.get(URL).mock(
        side_effect=[httpx.Response(200, json=body[0]), httpx.Response(200, json=body)]
    )
    assert len(_client().hourly(POINTS, START, END)) == 2


@respx.mock
def test_timeouts_are_retried_then_reported_as_busy(no_backoff: None) -> None:
    route = respx.get(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(TransientUpstreamError) as info:
        _client().hourly(POINTS, START, END)
    assert route.call_count == 3
    assert info.value.details["cause"] == "ReadTimeout"


@respx.mock
def test_timeout_then_success_recovers(no_backoff: None) -> None:
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    route = respx.get(URL).mock(
        side_effect=[httpx.ReadTimeout("slow"), httpx.Response(200, json=body)]
    )
    assert len(_client().hourly(POINTS, START, END)) == 2
    assert route.call_count == 2


def test_empty_points_short_circuit() -> None:
    assert _client().hourly([], START, END) == []


@respx.mock
def test_rate_limit_is_retried_once_then_surfaces_as_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "RETRY_BACKOFF_SECONDS", 0)
    route = respx.get(URL).mock(
        return_value=httpx.Response(429, json={"reason": "Minutely API request limit exceeded"})
    )
    with pytest.raises(RateLimitedError) as info:
        _client().hourly(POINTS, START, END)
    assert route.call_count == 3  # initial + 2 retries
    assert info.value.code == "rate_limited"
    assert info.value.http_status == 503
    assert "try again" in info.value.message


@respx.mock
def test_overloaded_upstream_is_treated_as_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "RETRY_BACKOFF_SECONDS", 0)
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(503, json={"reason": "The service is overloaded"}),
            httpx.Response(200, json=body),
        ]
    )
    assert len(_client().hourly(POINTS, START, END)) == 2
    assert route.call_count == 2


@respx.mock
def test_rate_limit_then_success_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "RETRY_BACKOFF_SECONDS", 0)
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    respx.get(URL).mock(side_effect=[httpx.Response(429, json={}), httpx.Response(200, json=body)])
    assert len(_client().hourly(POINTS, START, END)) == 2


@respx.mock
def test_requested_fields_are_configurable() -> None:
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=body))
    _client().hourly(POINTS, START, END, fields=("wind_speed_10m", "rain", "showers", "snowfall"))
    assert route.calls.last.request.url.params["hourly"] == "wind_speed_10m,rain,showers,snowfall"


@respx.mock
def test_missing_values_stay_unknown_instead_of_becoming_zero() -> None:
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())[0]
    body["hourly"]["wind_speed_10m"] = [None, 30.0, 58.0]
    body["hourly"]["rain"] = [None, 0.2, None]
    body["hourly"]["showers"] = [None, 0.1, 0.0]
    respx.get(URL).mock(return_value=httpx.Response(200, json=body))

    series = _client().hourly([POINTS[0]], START, END)[0]

    assert series.wind_mph[0] is None
    assert series.rain_in == [
        None,
        pytest.approx(0.3),
        0.0,
    ]  # rain + showers; one present is enough
    # 08:10 needs the 08:00 wind reading, which is missing, so the sample is unknown.
    assert series.sample_at(START.replace(minute=10)) is None
