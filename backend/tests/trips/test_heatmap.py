from __future__ import annotations

from datetime import UTC, datetime

from apps.geo.types import GeoPoint, Place
from apps.risk.engine import WeatherSample
from apps.trips.services.heatmap import build_heatmap, corridor_grid
from apps.trips.services.planner import PlanRequest, TripPlanner
from tests.geo.helpers import straight_route
from tests.trips.fakes import FakeGeo, FakeWeather, calm


def test_corridor_grid_stays_near_routes_and_respects_max_points() -> None:
    route = [[lon / 10, 0.0] for lon in range(0, 31)]  # 3 degrees east along the equator
    grid = corridor_grid([route], bounds=[[0.0, 0.0], [3.0, 0.0]], max_points=120)

    assert 0 < len(grid) <= 120
    assert all(abs(p.lat) < 0.8 for p in grid)  # ~35 mile corridor + padding, never far away
    assert min(p.lon for p in grid) < 0.2 and max(p.lon for p in grid) > 2.8


def test_corridor_grid_thins_when_over_budget() -> None:
    route = [[lon / 10, lat / 10] for lon in range(0, 60) for lat in (0, 20)]
    grid = corridor_grid([route], bounds=[[0.0, 0.0], [6.0, 2.0]], max_points=50)
    assert len(grid) <= 50


def test_build_heatmap_emits_levels_per_hour_for_each_point() -> None:
    route = straight_route("r", total_miles=60, lat=0.0)
    plan = TripPlanner(geo=FakeGeo([route]), weather=FakeWeather(calm)).plan(  # type: ignore[arg-type]
        PlanRequest(
            Place("A", "A", GeoPoint(0, 0)),
            Place("B", "B", GeoPoint(0, 1)),
            datetime(2026, 10, 20, 8, 30, tzinfo=UTC),
            45_000,
            25,
        )
    )

    def windy_afternoon(point: GeoPoint, when: datetime) -> WeatherSample:
        wind = 40 if when.hour >= 15 else 5
        return WeatherSample(wind_mph=wind, rain_in_per_hr=0, snow_in_per_hr=0)

    heatmap = build_heatmap(plan, weather=FakeWeather(windy_afternoon), max_points=30)  # type: ignore[arg-type]

    assert heatmap["start"] == "2026-10-20T08:00:00+00:00"
    assert len(heatmap["hours"]) == 49
    assert 0 < len(heatmap["points"]) <= 30
    first = heatmap["points"][0]
    assert len(first["levels"]) == 49 and len(first["wind_mph"]) == 49
    # 08:00-14:00 calm (0 = Low); 15:00 onwards 40 mph + 45k lb load -> Severe (3)
    assert first["levels"][0] == 0
    assert first["levels"][7] == 3


def test_hours_without_a_forecast_are_unknown_not_low() -> None:
    route = straight_route("r", total_miles=60, lat=0.0)
    plan = TripPlanner(geo=FakeGeo([route]), weather=FakeWeather(calm)).plan(  # type: ignore[arg-type]
        PlanRequest(
            Place("A", "A", GeoPoint(0, 0)),
            Place("B", "B", GeoPoint(0, 1)),
            datetime(2026, 10, 20, 8, 30, tzinfo=UTC),
            20_000,
            25,
        )
    )

    def gap_after_noon(point: GeoPoint, when: datetime) -> WeatherSample | None:
        return None if when.hour >= 12 else calm(point, when)

    heatmap = build_heatmap(plan, weather=FakeWeather(gap_after_noon), max_points=10)  # type: ignore[arg-type]

    levels = heatmap["points"][0]["levels"]
    assert levels[0] == 0  # 08:00, known and calm
    assert levels[5] is None  # 13:00, no forecast
