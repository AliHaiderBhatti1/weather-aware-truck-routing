"""Provider-agnostic interfaces so Mapbox can be swapped (or faked in tests)."""

from __future__ import annotations

from typing import Protocol

from apps.geo.types import GeoPoint, Place, Route


class GeocodingProvider(Protocol):
    def search(self, query: str, *, limit: int = 5) -> list[Place]: ...


class RoutingProvider(Protocol):
    def routes(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        alternatives: bool = True,
        exclude: str | None = None,
    ) -> list[Route]: ...
