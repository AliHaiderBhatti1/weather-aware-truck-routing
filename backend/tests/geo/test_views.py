from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.geo.types import GeoPoint, Place


@pytest.mark.django_db
def test_geocode_endpoint_validates_query(api_client: APIClient) -> None:
    response = api_client.get("/api/geocode/", {"q": "a"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid"
    assert "q" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_geocode_endpoint_returns_places(api_client: APIClient) -> None:
    place = Place("Denver", "Denver, Colorado, United States", GeoPoint(39.74, -104.99), "place")
    with patch("apps.geo.views.GeoService.search", return_value=[place]) as search:
        response = api_client.get("/api/geocode/", {"q": "Denv", "limit": "3"})

    search.assert_called_once_with("Denv", limit=3)
    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "Denver",
            "full_name": "Denver, Colorado, United States",
            "lat": 39.74,
            "lon": -104.99,
            "kind": "place",
        }
    ]
