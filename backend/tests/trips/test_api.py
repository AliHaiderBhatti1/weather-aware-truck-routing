from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from freezegun import freeze_time
from rest_framework.test import APIClient

from apps.geo.types import GeoPoint, Place
from apps.trips.models import TripPlan
from apps.trips.services.planner import TripPlanner
from tests.geo.helpers import straight_route
from tests.trips.fakes import FakeGeo, FakeWeather, calm

NOW = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
PLACES = {
    "Denver": Place("Denver", "Denver, CO", GeoPoint(0, 0)),
    "SLC": Place("Salt Lake City", "Salt Lake City, UT", GeoPoint(0, 1.4)),
}


def _fake_planner() -> TripPlanner:
    routes = [
        straight_route("a", lat=0.0),
        straight_route("b", lat=0.3),
        straight_route("c", lat=0.6),
    ]
    return TripPlanner(geo=FakeGeo(routes, PLACES), weather=FakeWeather(calm))  # type: ignore[arg-type]


def _body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "origin": {"query": "Denver"},
        "destination": {"query": "SLC"},
        "departure_time": (NOW + timedelta(hours=2)).isoformat(),
        "load_weight_lb": 30000,
        "checkpoint_interval_miles": 25,
    }
    body.update(overrides)
    return body


@pytest.mark.django_db
@freeze_time(NOW)
def test_create_plan_persists_and_returns_it(api_client: APIClient) -> None:
    with patch("apps.trips.views.TripPlanner", return_value=_fake_planner()):
        response = api_client.post("/api/trips/", _body(), format="json")

    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["recommended_route_id"] == "a"
    assert len(data["routes"]) == 3
    assert data["request"]["origin"]["full_name"] == "Denver, CO"

    stored = TripPlan.objects.get(pk=data["id"])
    assert stored.result["recommended_route_id"] == "a"

    detail = api_client.get(f"/api/trips/{data['id']}/")
    assert detail.status_code == 200
    assert detail.json()["id"] == data["id"]


@pytest.mark.django_db
@freeze_time(NOW)
def test_create_plan_accepts_coordinates(api_client: APIClient) -> None:
    body = _body(origin={"lat": 0.0, "lon": 0.0, "name": "Pinned start"})
    with patch("apps.trips.views.TripPlanner", return_value=_fake_planner()):
        response = api_client.post("/api/trips/", body, format="json")
    assert response.status_code == 201
    assert response.json()["request"]["origin"]["name"] == "Pinned start"


@pytest.mark.django_db
@freeze_time(NOW)
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"departure_time": (NOW - timedelta(hours=3)).isoformat()}, "departure_time"),
        ({"departure_time": (NOW + timedelta(days=20)).isoformat()}, "departure_time"),
        ({"load_weight_lb": -5}, "load_weight_lb"),
        ({"checkpoint_interval_miles": 15}, "checkpoint_interval_miles"),
        ({"origin": {"name": "no coords"}}, "origin"),
        ({"origin": {"lat": 1.0}}, "origin"),
    ],
)
def test_create_plan_validation_errors(
    api_client: APIClient, overrides: dict[str, object], field: str
) -> None:
    response = api_client.post("/api/trips/", _body(**overrides), format="json")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid"
    assert field in error["details"]


@pytest.mark.django_db
@freeze_time(NOW)
def test_domain_errors_use_the_error_envelope(api_client: APIClient) -> None:
    from apps.trips.exceptions import GeocodingError

    class Broken(FakeGeo):
        def resolve(self, query: str) -> Place:
            raise GeocodingError(f"Could not find '{query}'.", details={"query": query})

    planner = TripPlanner(geo=Broken([]), weather=FakeWeather(calm))  # type: ignore[arg-type]
    with patch("apps.trips.views.TripPlanner", return_value=planner):
        response = api_client.post("/api/trips/", _body(), format="json")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "geocoding_failed",
            "message": "Could not find 'Denver'.",
            "details": {"query": "Denver"},
        }
    }


@pytest.mark.django_db
def test_unknown_plan_is_404(api_client: APIClient) -> None:
    response = api_client.get("/api/trips/00000000-0000-0000-0000-000000000000/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.django_db
@freeze_time(NOW)
def test_heatmap_is_computed_once_and_cached_on_the_plan(api_client: APIClient) -> None:
    with patch("apps.trips.views.TripPlanner", return_value=_fake_planner()):
        plan_id = api_client.post("/api/trips/", _body(), format="json").json()["id"]

    with patch("apps.trips.views.build_heatmap", return_value={"points": [], "hours": []}) as build:
        first = api_client.get(f"/api/trips/{plan_id}/heatmap/")
        second = api_client.get(f"/api/trips/{plan_id}/heatmap/")

    assert first.status_code == second.status_code == 200
    assert build.call_count == 1
    assert TripPlan.objects.get(pk=plan_id).heatmap == {"points": [], "hours": []}


@pytest.mark.django_db
@freeze_time(NOW)
def test_incomplete_heatmaps_are_served_but_not_stored(api_client: APIClient) -> None:
    with patch("apps.trips.views.TripPlanner", return_value=_fake_planner()):
        plan_id = api_client.post("/api/trips/", _body(), format="json").json()["id"]

    partial = {"complete": False, "points": [], "hours": []}
    with patch("apps.trips.views.build_heatmap", return_value=partial) as build:
        api_client.get(f"/api/trips/{plan_id}/heatmap/")
        api_client.get(f"/api/trips/{plan_id}/heatmap/")

    assert build.call_count == 2  # recomputed until complete
    assert TripPlan.objects.get(pk=plan_id).heatmap is None
