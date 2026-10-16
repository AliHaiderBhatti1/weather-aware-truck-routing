from apps.geo.simplify import simplify


def test_collinear_points_collapse_to_endpoints() -> None:
    line = [(float(i), 0.0) for i in range(100)]
    assert simplify(line, 0.01) == [(0.0, 0.0), (99.0, 0.0)]


def test_significant_corners_are_kept() -> None:
    line = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (2.0, 1.0)]
    assert simplify(line, 0.1) == line


def test_small_wiggles_are_removed_but_large_ones_kept() -> None:
    line = [(0.0, 0.0), (1.0, 0.001), (2.0, 0.0), (3.0, 0.5), (4.0, 0.0)]
    assert simplify(line, 0.01) == [(0.0, 0.0), (2.0, 0.0), (3.0, 0.5), (4.0, 0.0)]


def test_short_inputs_are_returned_unchanged() -> None:
    assert simplify([(0.0, 0.0), (1.0, 1.0)], 1.0) == [(0.0, 0.0), (1.0, 1.0)]
    assert simplify([], 1.0) == []
