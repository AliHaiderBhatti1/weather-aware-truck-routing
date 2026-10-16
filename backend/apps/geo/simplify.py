"""Iterative Ramer-Douglas-Peucker line simplification for lean map payloads."""

from __future__ import annotations

Coordinate = tuple[float, float]


def simplify(points: list[Coordinate], tolerance: float) -> list[Coordinate]:
    """Drop points that deviate less than ``tolerance`` (same units as the input) from the line."""
    if len(points) < 3 or tolerance <= 0:
        return list(points)

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack: list[tuple[int, int]] = [(0, len(points) - 1)]
    tolerance_sq = tolerance * tolerance

    while stack:
        first, last = stack.pop()
        max_dist_sq = 0.0
        index = first
        for i in range(first + 1, last):
            dist_sq = _segment_distance_sq(points[i], points[first], points[last])
            if dist_sq > max_dist_sq:
                max_dist_sq, index = dist_sq, i
        if max_dist_sq > tolerance_sq:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))

    return [point for point, flag in zip(points, keep, strict=True) if flag]


def _segment_distance_sq(p: Coordinate, a: Coordinate, b: Coordinate) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return (px - ax) ** 2 + (py - ay) ** 2
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2
