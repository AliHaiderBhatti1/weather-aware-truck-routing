"""Mapbox Geocoding v6 + Directions v5 adapter."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings

from apps.geo.types import GeoPoint, Place, Route
from apps.trips.exceptions import ConfigurationError, RoutingError, UpstreamError

logger = logging.getLogger(__name__)


class MapboxClient:
    def __init__(
        self,
        access_token: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        http: httpx.Client | None = None,
    ) -> None:
        self._token = access_token if access_token is not None else settings.MAPBOX_ACCESS_TOKEN
        self._base_url = (base_url or settings.MAPBOX_BASE_URL).rstrip("/")
        self._http = http or httpx.Client(timeout=timeout or settings.UPSTREAM_TIMEOUT_SECONDS)

    # -- helpers ---------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._token:
            raise ConfigurationError("MAPBOX_ACCESS_TOKEN is not configured on the server.")
        try:
            response = self._http.get(
                f"{self._base_url}{path}", params={**params, "access_token": self._token}
            )
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Mapbox request failed: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            body = _safe_json(response)
            message = body.get("message") if isinstance(body, dict) else None
            logger.warning("Mapbox %s -> %s %s", path, response.status_code, message)
            if response.status_code == 422:
                # Invalid input for the routing engine (too far, unroutable area...)
                # is the caller's problem, not an outage.
                raise RoutingError(_friendly_routing_message(message), details={"message": message})
            raise UpstreamError(
                f"Mapbox returned HTTP {response.status_code}",
                details={"message": message} if message else None,
            )
        data = _safe_json(response)
        if not isinstance(data, dict):
            raise UpstreamError("Mapbox returned an unexpected payload")
        return data

    # -- geocoding -------------------------------------------------------

    def search(self, query: str, *, limit: int = 5) -> list[Place]:
        data = self._get(
            "/search/geocode/v6/forward",
            {
                "q": query,
                "limit": limit,
                "autocomplete": "true",
                "types": "place,locality,neighborhood,address,street,postcode,region,district",
            },
        )
        places: list[Place] = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = props.get("coordinates") or {}
            lon, lat = coords.get("longitude"), coords.get("latitude")
            if lon is None or lat is None:
                geometry = feature.get("geometry", {}).get("coordinates")
                if not geometry:
                    continue
                lon, lat = geometry
            places.append(
                Place(
                    name=props.get("name") or props.get("full_address") or query,
                    full_name=props.get("full_address") or props.get("place_formatted") or query,
                    point=GeoPoint(float(lat), float(lon)),
                    kind=props.get("feature_type", "place"),
                )
            )
        return places

    # -- routing ---------------------------------------------------------

    def routes(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        alternatives: bool = True,
        exclude: str | None = None,
    ) -> list[Route]:
        coords = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
        params: dict[str, Any] = {
            "alternatives": "true" if alternatives else "false",
            "geometries": "geojson",
            "overview": "full",
            "annotations": "distance,duration",
            "steps": "false",
        }
        if exclude:
            params["exclude"] = exclude
        data = self._get(f"/directions/v5/mapbox/driving/{coords}", params)
        code = data.get("code")
        if code != "Ok":
            if code == "NoSegment":
                raise RoutingError(
                    "Could not find a road near the origin or destination. "
                    "Pick a point on land close to a road.",
                    details={"code": code},
                )
            if code == "NoRoute":
                raise RoutingError(
                    "No driveable route connects those places.", details={"code": code}
                )
            raise UpstreamError(f"Mapbox Directions returned {code}", details={"code": code})

        routes: list[Route] = []
        for index, raw in enumerate(data.get("routes", [])):
            route = _parse_route(raw, index, exclude)
            if route is not None:
                routes.append(route)
        return routes


def _parse_route(raw: dict[str, Any], index: int, exclude: str | None) -> Route | None:
    coordinates = [tuple(pair) for pair in raw.get("geometry", {}).get("coordinates", [])]
    if len(coordinates) < 2:
        return None
    distances: list[float] = []
    durations: list[float] = []
    summaries: list[str] = []
    for leg in raw.get("legs", []):
        annotation = leg.get("annotation", {})
        distances.extend(float(value) for value in annotation.get("distance", []))
        durations.extend(float(value) for value in annotation.get("duration", []))
        if leg.get("summary"):
            summaries.append(str(leg["summary"]))
    if len(distances) != len(coordinates) - 1 or len(durations) != len(coordinates) - 1:
        logger.warning("Mapbox route %s annotations do not match geometry; skipping", index)
        return None
    source = (
        "fastest"
        if index == 0 and not exclude
        else ("alternative" if not exclude else f"no-{exclude}")
    )
    return Route(
        id=f"mapbox-{source}-{index}",
        name=", ".join(summaries) or f"Route {index + 1}",
        source=source,
        distance_m=float(raw["distance"]),
        duration_s=float(raw["duration"]),
        coordinates=[(float(lon), float(lat)) for lon, lat in coordinates],
        segment_distances_m=distances,
        segment_durations_s=durations,
    )


def _friendly_routing_message(message: str | None) -> str:
    text = (message or "").lower()
    if "distance" in text:
        return "That trip is too long to route by road."
    if "coordinate" in text:
        return "One of the places has invalid coordinates."
    return f"The routing service rejected the request: {message or 'invalid input'}."


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
