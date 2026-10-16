from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from apps.geo.providers.mapbox import MapboxClient
from apps.geo.types import GeoPoint
from apps.trips.exceptions import ConfigurationError, RoutingError, UpstreamError

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
BASE = "https://mapbox.test"


def _client() -> MapboxClient:
    return MapboxClient(access_token="tok", base_url=BASE, timeout=5)


@respx.mock
def test_directions_parsing_skips_malformed_routes() -> None:
    route = respx.get(url__regex=rf"{BASE}/directions/v5/mapbox/driving/.*").mock(
        return_value=httpx.Response(
            200, json=json.loads((FIXTURES / "mapbox_directions.json").read_text())
        )
    )

    routes = _client().routes(GeoPoint(39.7, -105.0), GeoPoint(39.7, -104.97))

    assert route.called
    sent = route.calls.last.request.url
    assert "-105.0,39.7;-104.97,39.7" in str(sent)
    assert sent.params["alternatives"] == "true"
    assert sent.params["annotations"] == "distance,duration"
    assert sent.params["access_token"] == "tok"

    assert len(routes) == 2  # third fixture route has mismatched annotations
    assert routes[0].name == "I-70 E, US-6"
    assert routes[0].source == "fastest"
    assert routes[1].source == "alternative"
    assert routes[0].distance_m == 3000.0
    assert routes[0].segment_durations_s == [60.0, 60.0, 60.0]


@respx.mock
def test_directions_exclude_parameter_and_source_label() -> None:
    respx.get(url__regex=rf"{BASE}/directions/.*").mock(
        return_value=httpx.Response(
            200, json=json.loads((FIXTURES / "mapbox_directions.json").read_text())
        )
    )
    routes = _client().routes(GeoPoint(39.7, -105.0), GeoPoint(39.7, -104.97), exclude="toll")
    assert respx.calls.last.request.url.params["exclude"] == "toll"
    assert routes[0].source == "no-toll"


@respx.mock
def test_directions_no_route_maps_to_domain_error() -> None:
    respx.get(url__regex=rf"{BASE}/directions/.*").mock(
        return_value=httpx.Response(200, json={"code": "NoRoute", "routes": []})
    )
    with pytest.raises(RoutingError):
        _client().routes(GeoPoint(0, 0), GeoPoint(1, 1))


@respx.mock
def test_http_errors_map_to_upstream_error() -> None:
    respx.get(url__regex=rf"{BASE}/directions/.*").mock(
        return_value=httpx.Response(401, json={"message": "Not Authorized - Invalid Token"})
    )
    with pytest.raises(UpstreamError) as info:
        _client().routes(GeoPoint(0, 0), GeoPoint(1, 1))
    assert info.value.details == {"message": "Not Authorized - Invalid Token"}


@respx.mock
def test_network_failure_maps_to_upstream_error() -> None:
    respx.get(url__regex=rf"{BASE}/directions/.*").mock(side_effect=httpx.ConnectTimeout("slow"))
    with pytest.raises(UpstreamError, match="ConnectTimeout"):
        _client().routes(GeoPoint(0, 0), GeoPoint(1, 1))


def test_missing_token_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        MapboxClient(access_token="", base_url=BASE).search("Denver")


@respx.mock
def test_geocode_parsing() -> None:
    respx.get(url__regex=rf"{BASE}/search/geocode/v6/forward.*").mock(
        return_value=httpx.Response(
            200, json=json.loads((FIXTURES / "mapbox_geocode.json").read_text())
        )
    )

    places = _client().search("Denver", limit=2)

    assert respx.calls.last.request.url.params["q"] == "Denver"
    assert places[0].name == "Denver"
    assert places[0].full_name == "Denver, Colorado, United States"
    assert places[0].point == GeoPoint(39.7392, -104.9847)
    assert places[1].point == GeoPoint(40.0, -83.0)  # falls back to geometry
    assert places[1].kind == "street"
