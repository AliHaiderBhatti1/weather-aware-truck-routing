"""
Geo use-cases: cached geocoding and "give me three distinct routes".

Mapbox returns at most two alternatives alongside the fastest route and often
fewer on long trips. To honour the brief's "3 route options" we top up with
toll-free and motorway-free variants, then drop near-duplicates by geometric
overlap.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import TypeVar

from django.conf import settings
from django.core.cache import cache

from apps.geo.providers.base import GeocodingProvider, RoutingProvider
from apps.geo.providers.mapbox import MapboxClient
from apps.geo.sampling import densify
from apps.geo.types import GeoPoint, Place, Route
from apps.geo.units import meters_to_miles, miles_to_meters
from apps.trips.exceptions import GeocodingError, RoutingError, UpstreamError

logger = logging.getLogger(__name__)

T = TypeVar("T")

TARGET_ROUTE_COUNT = 3
FALLBACK_EXCLUSIONS = ("toll", "motorway")
OVERLAP_SAMPLE_MILES = 5.0
OVERLAP_TOLERANCE_M = miles_to_meters(1.0)
DUPLICATE_OVERLAP = 0.85

SOURCE_LABELS = {
    "fastest": "Fastest",
    "alternative": "Alternative",
    "no-toll": "Avoids tolls",
    "no-motorway": "Avoids motorways",
}


def _cached(key: str, ttl: int, compute: Callable[[], T]) -> T:
    hit = cache.get(key)
    if hit is not None:
        return hit  # type: ignore[no-any-return]
    value = compute()
    cache.set(key, value, ttl)
    return value


def _hash(*parts: object) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:20]


class GeoService:
    def __init__(
        self,
        geocoder: GeocodingProvider | None = None,
        router: RoutingProvider | None = None,
    ) -> None:
        client = MapboxClient() if geocoder is None or router is None else None
        self._geocoder: GeocodingProvider = geocoder or client  # type: ignore[assignment]
        self._router: RoutingProvider = router or client  # type: ignore[assignment]

    # -- geocoding -------------------------------------------------------

    def search(self, query: str, *, limit: int = 5) -> list[Place]:
        query = " ".join(query.split())
        if len(query) < 2:
            return []
        return _cached(
            f"geocode:{_hash(query.lower(), limit)}",
            settings.GEOCODE_CACHE_TTL,
            lambda: self._geocoder.search(query, limit=limit),
        )

    def resolve(self, query: str) -> Place:
        """Best match for a free-text place, or raise ``GeocodingError``."""
        places = self.search(query, limit=1)
        if not places:
            raise GeocodingError(
                f"Could not find a place matching '{query}'.", details={"query": query}
            )
        return places[0]

    # -- routing ---------------------------------------------------------

    def route_options(self, origin: GeoPoint, destination: GeoPoint) -> list[Route]:
        """Up to three distinct routes, fastest first."""
        straight_line_m = origin.distance_to(destination)
        if straight_line_m < 500:
            raise RoutingError("Origin and destination are the same place.")
        limit_miles = settings.MAX_ROUTE_DISTANCE_MILES
        if straight_line_m > miles_to_meters(limit_miles):
            # Road distance is never shorter than the great-circle distance, so
            # this rejects intercontinental pairs without an upstream call.
            raise RoutingError(
                f"Trips longer than {limit_miles:,.0f} miles are not supported "
                f"(these places are {meters_to_miles(straight_line_m):,.0f} miles apart).",
                details={"straight_line_miles": round(meters_to_miles(straight_line_m))},
            )

        # Mapbox rarely returns three alternatives, so the toll-free and
        # motorway-free variants are requested concurrently with the primary
        # call instead of as sequential fallbacks (saves ~2 s per plan).
        variants: list[str | None] = [None, *FALLBACK_EXCLUSIONS]
        with ThreadPoolExecutor(max_workers=len(variants)) as pool:
            futures = {
                exclusion: pool.submit(self._routes, origin, destination, exclude=exclusion)
                for exclusion in variants
            }

        routes = list(futures[None].result())
        if not routes:
            raise RoutingError("No driveable route found between those places.")

        for exclusion in FALLBACK_EXCLUSIONS:
            if len(routes) >= TARGET_ROUTE_COUNT:
                break
            try:
                extra = futures[exclusion].result()
            except (RoutingError, UpstreamError) as exc:
                logger.info("Fallback routing (exclude=%s) failed: %s", exclusion, exc)
                continue
            routes = _merge_distinct(routes, extra)

        routes = routes[:TARGET_ROUTE_COUNT]
        longest_allowed = miles_to_meters(settings.MAX_ROUTE_DISTANCE_MILES)
        if routes[0].distance_m > longest_allowed:
            raise RoutingError(
                f"Trips longer than {limit_miles:,.0f} miles by road are not supported "
                f"(the fastest route is {routes[0].distance_miles:,.0f} miles).",
                details={"distance_miles": round(routes[0].distance_miles)},
            )
        return [
            replace(route, id=f"route-{index + 1}", name=_display_name(route))
            for index, route in enumerate(routes)
        ]

    def _routes(
        self, origin: GeoPoint, destination: GeoPoint, *, exclude: str | None
    ) -> list[Route]:
        key = f"routes:{_hash(origin.rounded(), destination.rounded(), exclude)}"
        return _cached(
            key,
            settings.ROUTE_CACHE_TTL,
            lambda: self._router.routes(origin, destination, alternatives=True, exclude=exclude),
        )


def _display_name(route: Route) -> str:
    label = SOURCE_LABELS.get(route.source, route.source.title())
    return (
        f"{route.name} ({label})" if route.name and not route.name.startswith("Route ") else label
    )


def _merge_distinct(existing: list[Route], candidates: Iterable[Route]) -> list[Route]:
    merged = list(existing)
    for candidate in candidates:
        if len(merged) >= TARGET_ROUTE_COUNT:
            break
        if all(overlap(candidate, known) < DUPLICATE_OVERLAP for known in merged):
            merged.append(candidate)
    return merged


def overlap(a: Route, b: Route) -> float:
    """Fraction of ``a``'s sampled points that lie within a mile of ``b``."""
    pts_a = densify(a, OVERLAP_SAMPLE_MILES)
    pts_b = densify(b, OVERLAP_SAMPLE_MILES)
    if not pts_a or not pts_b:
        return 0.0
    # Coarse spatial bucketing keeps this O(n) for long routes.
    buckets: dict[tuple[int, int], list[GeoPoint]] = {}
    for p in pts_b:
        buckets.setdefault(_bucket(p), []).append(p)
    near = 0
    for p in pts_a:
        bx, by = _bucket(p)
        neighbours = (
            q for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in buckets.get((bx + dx, by + dy), ())
        )
        if any(p.distance_to(q) <= OVERLAP_TOLERANCE_M for q in neighbours):
            near += 1
    return near / len(pts_a)


def _bucket(p: GeoPoint, size_deg: float = 0.02) -> tuple[int, int]:
    return int(p.lat // size_deg), int(p.lon // size_deg)
