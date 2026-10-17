from __future__ import annotations

import pytest
from django.core.cache import cache

from apps.geo.service import GeoService, overlap
from apps.geo.types import GeoPoint, Place, Route
from apps.trips.exceptions import GeocodingError, RoutingError
from tests.geo.helpers import MILES_PER_DEGREE_LON_AT_EQUATOR, straight_route


class FakeGeocoder:
    def __init__(self, places: list[Place]) -> None:
        self.places = places
        self.calls = 0

    def search(self, query: str, *, limit: int = 5) -> list[Place]:
        self.calls += 1
        return self.places[:limit]


class FakeRouter:
    def __init__(self, by_exclusion: dict[str | None, list[Route]]) -> None:
        self.by_exclusion = by_exclusion
        self.calls: list[str | None] = []

    def routes(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        alternatives: bool = True,
        exclude: str | None = None,
    ) -> list[Route]:
        self.calls.append(exclude)
        if exclude not in self.by_exclusion:
            raise RoutingError("none")
        return self.by_exclusion[exclude]


ORIGIN = GeoPoint(0.0, 0.0)
DEST = GeoPoint(0.0, 1.5)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@pytest.mark.parametrize("offset_miles", [0.7, 1.5, 2.5, 4.9])
def test_overlap_ignores_where_sample_points_happen_to_fall(offset_miles: float) -> None:
    # Same road, but the second route starts a little further along, so its
    # 5-mile samples sit between the first route's samples.
    a = straight_route("a", total_miles=100, segments=10, lat=0.0)
    shifted = straight_route(
        "b",
        total_miles=100,
        segments=10,
        lat=0.0,
        lon_start=offset_miles / MILES_PER_DEGREE_LON_AT_EQUATOR,
    )
    assert overlap(a, shifted) >= 0.9
    assert overlap(shifted, a) >= 0.9


def test_overlap_detects_identical_and_distinct_routes() -> None:
    a = straight_route("a", lat=0.0)
    same = straight_route("b", lat=0.0)
    far = straight_route("c", lat=0.5)  # ~34 miles north
    assert overlap(a, same) == pytest.approx(1.0)
    assert overlap(a, far) == 0.0


def test_route_options_returns_provider_routes_when_three_available() -> None:
    router = FakeRouter(
        {
            None: [
                straight_route("a", lat=0.0),
                straight_route("b", lat=0.3),
                straight_route("c", lat=0.6),
            ]
        }
    )
    service = GeoService(geocoder=FakeGeocoder([]), router=router)

    routes = service.route_options(ORIGIN, DEST)

    assert [r.id for r in routes] == ["route-1", "route-2", "route-3"]
    assert set(router.calls) == {None, "toll", "motorway"}  # fetched concurrently


def test_route_options_tops_up_with_exclusions_and_drops_duplicates() -> None:
    fastest = straight_route("a", lat=0.0, source="fastest")
    toll_free_duplicate = straight_route("t", lat=0.001, source="no-toll")  # same corridor
    motorway_free = straight_route("m", lat=0.4, source="no-motorway")
    router = FakeRouter(
        {None: [fastest], "toll": [toll_free_duplicate], "motorway": [motorway_free]}
    )
    service = GeoService(geocoder=FakeGeocoder([]), router=router)

    routes = service.route_options(ORIGIN, DEST)

    assert set(router.calls) == {None, "toll", "motorway"}
    assert [r.source for r in routes] == ["fastest", "no-motorway"]
    assert routes[1].name.endswith("(Avoids motorways)")


def test_route_options_survives_failed_fallback_calls() -> None:
    router = FakeRouter({None: [straight_route("a")]})
    routes = GeoService(geocoder=FakeGeocoder([]), router=router).route_options(ORIGIN, DEST)
    assert len(routes) == 1
    assert set(router.calls) == {None, "toll", "motorway"}


def test_route_options_rejects_same_place() -> None:
    service = GeoService(geocoder=FakeGeocoder([]), router=FakeRouter({}))
    with pytest.raises(RoutingError, match="same place"):
        service.route_options(ORIGIN, GeoPoint(0.0, 0.001))


def test_route_options_rejects_overlong_trip(settings: object) -> None:
    settings.MAX_ROUTE_DISTANCE_MILES = 50  # type: ignore[attr-defined]
    router = FakeRouter({None: [straight_route("a", total_miles=100)]})
    with pytest.raises(RoutingError, match="not supported"):
        GeoService(geocoder=FakeGeocoder([]), router=router).route_options(ORIGIN, DEST)


def test_routes_are_cached_per_endpoint_pair() -> None:
    router = FakeRouter(
        {
            None: [straight_route("a"), straight_route("b", lat=0.3), straight_route("c", lat=0.6)],
            "toll": [straight_route("t", lat=0.9)],
            "motorway": [straight_route("m", lat=1.2)],
        }
    )
    service = GeoService(geocoder=FakeGeocoder([]), router=router)
    service.route_options(ORIGIN, DEST)
    service.route_options(ORIGIN, DEST)
    assert len(router.calls) == 3  # second call fully served from cache


def test_resolve_returns_best_match_or_raises() -> None:
    place = Place("Denver", "Denver, Colorado, United States", GeoPoint(39.74, -104.99))
    geocoder = FakeGeocoder([place])
    service = GeoService(geocoder=geocoder, router=FakeRouter({}))

    assert service.resolve("denver") == place
    assert service.resolve("Denver ") == place  # normalised + cached
    assert geocoder.calls == 1

    empty = GeoService(geocoder=FakeGeocoder([]), router=FakeRouter({}))
    with pytest.raises(GeocodingError):
        empty.resolve("nowhere")


def test_route_options_rejects_intercontinental_pairs_before_calling_mapbox() -> None:
    router = FakeRouter({None: [straight_route("a")]})
    service = GeoService(geocoder=FakeGeocoder([]), router=router)
    new_delhi, salt_lake = GeoPoint(28.593, 77.189), GeoPoint(40.763, -111.89)

    with pytest.raises(RoutingError, match="miles apart"):
        service.route_options(new_delhi, salt_lake)
    assert router.calls == []
