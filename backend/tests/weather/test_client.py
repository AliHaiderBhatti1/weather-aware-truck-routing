from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from apps.geo.types import GeoPoint
from apps.trips.exceptions import UpstreamError
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
    monkeypatch.setattr(client_module, "MAX_LOCATIONS_PER_REQUEST", 2)
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(200, json=body),
            httpx.Response(200, json=body[0]),
        ]
    )

    series = _client().hourly([*POINTS, GeoPoint(41.0, -107.0)], START, END)

    assert route.call_count == 2
    assert len(series) == 3


@respx.mock
def test_error_responses_become_upstream_errors() -> None:
    respx.get(URL).mock(return_value=httpx.Response(400, json={"reason": "Invalid coordinates"}))
    with pytest.raises(UpstreamError) as info:
        _client().hourly(POINTS, START, END)
    assert info.value.details == {"reason": "Invalid coordinates"}


@respx.mock
def test_location_count_mismatch_is_rejected() -> None:
    body = json.loads((FIXTURES / "open_meteo_multi.json").read_text())
    respx.get(URL).mock(return_value=httpx.Response(200, json=body[:1]))
    with pytest.raises(UpstreamError, match="unexpected number"):
        _client().hourly(POINTS, START, END)


@respx.mock
def test_timeout_is_an_upstream_error() -> None:
    respx.get(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(UpstreamError, match="ReadTimeout"):
        _client().hourly(POINTS, START, END)


def test_empty_points_short_circuit() -> None:
    assert _client().hourly([], START, END) == []
