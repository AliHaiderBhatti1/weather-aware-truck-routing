from datetime import UTC, datetime, timedelta

import pytest

from apps.geo.sampling import densify, sample_checkpoints
from tests.geo.helpers import straight_route

DEPART = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)


def test_checkpoints_every_interval_plus_destination() -> None:
    route = straight_route(total_miles=100, segments=10, mph=50)

    checkpoints = sample_checkpoints(route, interval_miles=25, departure=DEPART)

    assert [round(c.distance_from_start_miles, 3) for c in checkpoints] == [0, 25, 50, 75, 100]
    assert [c.index for c in checkpoints] == [0, 1, 2, 3, 4]
    # Half-way to each neighbour: endpoints cover half a stretch.
    assert [round(c.segment_miles, 3) for c in checkpoints] == [12.5, 25, 25, 25, 12.5]
    assert sum(c.segment_miles for c in checkpoints) == pytest.approx(100)


def test_eta_is_departure_plus_interpolated_travel_time() -> None:
    route = straight_route(total_miles=100, segments=4, mph=50)  # 2h total

    checkpoints = sample_checkpoints(route, interval_miles=30, departure=DEPART)

    # 30 miles at 50 mph = 36 min
    assert checkpoints[1].eta == DEPART + timedelta(minutes=36)
    assert checkpoints[-1].eta == DEPART + timedelta(hours=2)
    assert checkpoints[-1].distance_from_start_miles == pytest.approx(100)


def test_positions_are_interpolated_inside_segments() -> None:
    route = straight_route(total_miles=100, segments=2, lat=0.0)
    checkpoints = sample_checkpoints(route, interval_miles=25, departure=DEPART)

    lons = [c.point.lon for c in checkpoints]
    assert lons == sorted(lons)
    # 25 miles is a quarter of the way between lon 0 and the end.
    assert checkpoints[1].point.lon == pytest.approx(route.coordinates[-1][0] / 4, rel=1e-6)
    assert all(c.point.lat == 0.0 for c in checkpoints)


def test_tiny_trailing_stub_is_merged_into_destination() -> None:
    route = straight_route(total_miles=51, segments=3)
    checkpoints = sample_checkpoints(route, interval_miles=25, departure=DEPART)
    # 0, 25, 50, 51 -> the 50 is dropped because 1 mile < 10% of 25
    assert [round(c.distance_from_start_miles, 2) for c in checkpoints] == [0, 25, 51]


def test_short_route_yields_origin_and_destination_only() -> None:
    route = straight_route(total_miles=8, segments=2)
    checkpoints = sample_checkpoints(route, interval_miles=50, departure=DEPART)
    assert len(checkpoints) == 2
    assert [c.segment_miles for c in checkpoints] == [pytest.approx(4), pytest.approx(4)]


def test_invalid_interval_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        sample_checkpoints(straight_route(), 0, DEPART)


def test_densify_spacing() -> None:
    route = straight_route(total_miles=20, segments=2)
    points = densify(route, every_miles=5)
    assert len(points) == 5
    assert points[0].distance_to(points[1]) == pytest.approx(5 * 1609.344, rel=1e-3)
