from __future__ import annotations

from datetime import UTC, datetime

from apps.geo.types import GeoPoint, Place
from apps.risk.engine import WeatherSample
from apps.trips.services.planner import PlanRequest, TripPlanner
from tests.geo.helpers import straight_route
from tests.trips.fakes import FakeGeo, FakeWeather, calm

DEPART = datetime(2026, 10, 20, 8, 30, tzinfo=UTC)
ORIGIN = Place("A", "A town", GeoPoint(0, 0))
DEST = Place("B", "B city", GeoPoint(0, 1.4))


def _request(load: int = 20_000, interval: int = 25) -> PlanRequest:
    return PlanRequest(ORIGIN, DEST, DEPART, load, interval)


def test_plan_ranks_routes_by_risk_and_explains_recommendation() -> None:
    fast = straight_route("fast", total_miles=100, mph=60, lat=0.0)
    slow = straight_route("slow", total_miles=100, mph=40, lat=0.5)
    windy_mid = straight_route("windy", total_miles=100, mph=60, lat=1.0)

    def weather(point: GeoPoint, when: datetime) -> WeatherSample:
        # Severe wind on the fast route's middle, high wind along the whole 'windy' route.
        if point.lat == 0.0 and 0.3 < point.lon < 0.9:
            return WeatherSample(wind_mph=50, rain_in_per_hr=0, snow_in_per_hr=0)
        if point.lat == 1.0:
            return WeatherSample(wind_mph=40, rain_in_per_hr=0, snow_in_per_hr=0)
        return calm(point, when)

    fake_weather = FakeWeather(weather)
    planner = TripPlanner(geo=FakeGeo([fast, slow, windy_mid]), weather=fake_weather)  # type: ignore[arg-type]

    plan = planner.plan(_request(load=20_000))

    assert fake_weather.sample_calls == 1  # all checkpoints in one weather batch
    # 'windy' is High for all 100 miles but has no Severe miles, so it beats 'fast'.
    assert [r["id"] for r in plan["routes"]] == ["slow", "windy", "fast"]
    assert plan["recommended_route_id"] == "slow"
    assert plan["routes"][0]["recommended"] is True
    assert plan["routes"][0]["rank"] == 1
    assert plan["recommendation_reasons"] == [
        "fewest High miles vs. windy",
        "fewest Severe miles vs. fast",
    ]
    assert plan["warnings"] == []

    fast_payload = next(r for r in plan["routes"] if r["id"] == "fast")
    assert fast_payload["summary"]["severe_miles"] == 50.0  # checkpoints at 25 & 50 miles
    assert fast_payload["summary"]["max_level"] == "severe"
    levels = [cp["risk"]["level"] for cp in fast_payload["checkpoints"]]
    assert levels == ["low", "severe", "severe", "low", "low"]
    assert fast_payload["checkpoints"][1]["risk"]["dominant_factor"] == "wind"
    assert fast_payload["checkpoints"][1]["eta"] == "2026-10-20T08:55:00+00:00"
    assert fast_payload["arrival_time"] == "2026-10-20T10:10:00+00:00"


def test_heavy_load_turns_severe_wind_into_no_travel_and_blocks_recommendation() -> None:
    route = straight_route("only", total_miles=50, lat=0.0)

    def gale(point: GeoPoint, when: datetime) -> WeatherSample:
        return WeatherSample(wind_mph=50, rain_in_per_hr=0, snow_in_per_hr=0)

    planner = TripPlanner(geo=FakeGeo([route]), weather=FakeWeather(gale))  # type: ignore[arg-type]

    plan = planner.plan(_request(load=35_000))

    assert plan["recommended_route_id"] is None
    assert plan["routes"][0]["summary"]["travel_advised"] is False
    assert plan["routes"][0]["summary"]["no_travel_miles"] == 50.0
    assert plan["routes"][0]["checkpoints"][0]["risk"]["applied_rule"].startswith("Wind 45-54 mph")
    assert any("No-Travel" in w for w in plan["warnings"])
    assert any("Only 1 distinct route exists" in w for w in plan["warnings"])


def test_missing_weather_is_reported_and_excluded_from_totals() -> None:
    route = straight_route("r", total_miles=50, lat=0.0)

    def patchy(point: GeoPoint, when: datetime) -> WeatherSample | None:
        return None if point.lon == 0.0 else calm(point, when)

    plan = TripPlanner(geo=FakeGeo([route]), weather=FakeWeather(patchy)).plan(_request())  # type: ignore[arg-type]

    first = plan["routes"][0]["checkpoints"][0]
    assert first["weather"] is None and first["risk"] is None
    # Checkpoints at 25 and 50 miles cover 25 + 12.5 miles; the origin's 12.5 is unknown.
    assert plan["routes"][0]["summary"]["miles_by_level"]["low"] == 37.5
    assert plan["routes"][0]["summary"]["unknown_miles"] == 12.5
    assert any("unavailable for 1 checkpoint" in w for w in plan["warnings"])


def test_geometry_is_simplified_and_bounds_cover_all_routes() -> None:
    dense = straight_route("dense", total_miles=100, segments=500, lat=0.0)
    other = straight_route("other", total_miles=100, segments=4, lat=0.5)
    plan = TripPlanner(geo=FakeGeo([dense, other]), weather=FakeWeather(calm)).plan(_request())  # type: ignore[arg-type]

    dense_payload = next(r for r in plan["routes"] if r["id"] == "dense")
    assert len(dense_payload["geometry"]["coordinates"]) == 2  # collinear -> endpoints only
    assert plan["bounds"] == [[0.0, 0.0], [round(dense.coordinates[-1][0], 5), 0.5]]
    assert plan["forecast_window"]["start"] == "2026-10-20T08:00:00+00:00"
    assert plan["forecast_window"]["hours"] == 48


def test_resolve_place_prefers_coordinates_over_geocoding() -> None:
    planner = TripPlanner(geo=FakeGeo([], {"Denver": ORIGIN}), weather=FakeWeather(calm))  # type: ignore[arg-type]
    place = planner.resolve_place({"lat": 1.5, "lon": 2.5, "name": "Pinned"})
    assert place.point == GeoPoint(1.5, 2.5)
    assert place.name == "Pinned"
    assert planner.resolve_place({"query": "Denver"}) == ORIGIN


def test_no_travel_at_the_destination_blocks_the_recommendation() -> None:
    route = straight_route("r", total_miles=50, lat=0.0)
    end_lon = route.coordinates[-1][0]

    def deluge_on_arrival(point: GeoPoint, when: datetime) -> WeatherSample:
        if abs(point.lon - end_lon) < 1e-9:
            return WeatherSample(wind_mph=5, rain_in_per_hr=1.5, snow_in_per_hr=0)
        return calm(point, when)

    plan = TripPlanner(geo=FakeGeo([route]), weather=FakeWeather(deluge_on_arrival)).plan(  # type: ignore[arg-type]
        _request()
    )

    summary = plan["routes"][0]["summary"]
    assert summary["max_level"] == "no_travel"
    assert summary["no_travel_miles"] == 12.5  # the arrival half-stretch
    assert summary["travel_advised"] is False
    assert plan["recommended_route_id"] is None


def test_no_recommendation_when_forecasts_cover_too_little_of_every_route() -> None:
    route = straight_route("r", total_miles=50, lat=0.0)
    plan = TripPlanner(geo=FakeGeo([route]), weather=FakeWeather(lambda p, w: None)).plan(  # type: ignore[arg-type]
        _request()
    )

    assert plan["recommended_route_id"] is None
    assert plan["routes"][0]["summary"]["unknown_miles"] == 50.0
    assert any("Forecasts don't cover enough" in w for w in plan["warnings"])
    assert not any("No-Travel" in w for w in plan["warnings"])
