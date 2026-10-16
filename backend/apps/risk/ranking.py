"""
Route scoring and recommendation.

The brief's preference order is applied lexicographically:
    1. fewest Severe miles
    2. fewest High miles
    3. lowest average risk
    4. shortest travel time

``NO_TRAVEL`` is not in that ladder, so we treat it as a hard constraint that
sorts above everything else: any No-Travel miles push a route to the bottom and
disqualify it from being recommended.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from apps.risk.levels import RiskLevel


@dataclass(frozen=True, slots=True)
class RiskSegment:
    """A stretch of road governed by one checkpoint's assessment."""

    level: RiskLevel
    miles: float


@dataclass(frozen=True, slots=True)
class RouteRiskSummary:
    route_id: str
    duration_seconds: float
    total_miles: float
    miles_by_level: dict[RiskLevel, float]
    average_risk: float
    max_level: RiskLevel
    """Distance-weighted mean of the numeric level (0 = Low ... 4 = No Travel)."""

    @property
    def no_travel_miles(self) -> float:
        return self.miles_by_level.get(RiskLevel.NO_TRAVEL, 0.0)

    @property
    def severe_miles(self) -> float:
        return self.miles_by_level.get(RiskLevel.SEVERE, 0.0)

    @property
    def high_miles(self) -> float:
        return self.miles_by_level.get(RiskLevel.HIGH, 0.0)

    @property
    def is_travel_advised(self) -> bool:
        return self.no_travel_miles == 0.0

    def sort_key(self) -> tuple[float, float, float, float, float]:
        # Round so that floating point noise never decides a tie.
        return (
            round(self.no_travel_miles, 1),
            round(self.severe_miles, 1),
            round(self.high_miles, 1),
            round(self.average_risk, 2),
            round(self.duration_seconds),
        )


CRITERIA_LABELS: Sequence[str] = (
    "no No-Travel miles",
    "fewest Severe miles",
    "fewest High miles",
    "lowest average risk",
    "shortest travel time",
)


def summarize_route(
    route_id: str, duration_seconds: float, segments: Iterable[RiskSegment]
) -> RouteRiskSummary:
    miles_by_level: dict[RiskLevel, float] = {level: 0.0 for level in RiskLevel}
    weighted = 0.0
    total = 0.0
    max_level = RiskLevel.LOW
    for segment in segments:
        if segment.miles <= 0:
            continue
        miles_by_level[segment.level] += segment.miles
        weighted += int(segment.level) * segment.miles
        total += segment.miles
        max_level = max(max_level, segment.level)
    average = weighted / total if total else 0.0
    return RouteRiskSummary(
        route_id=route_id,
        duration_seconds=duration_seconds,
        total_miles=total,
        miles_by_level=miles_by_level,
        average_risk=average,
        max_level=max_level,
    )


@dataclass(frozen=True, slots=True)
class RankedRoute:
    summary: RouteRiskSummary
    rank: int
    """1 = best."""
    recommended: bool
    reasons: list[str] = field(default_factory=list)
    """Why this route beat the next best one (empty for non-winners)."""


def rank_routes(summaries: Sequence[RouteRiskSummary]) -> list[RankedRoute]:
    """Sort routes best-first and mark the recommended one, if any is travel-safe."""
    ordered = sorted(summaries, key=lambda summary: summary.sort_key())
    ranked: list[RankedRoute] = []
    for index, summary in enumerate(ordered):
        is_best = index == 0
        recommended = is_best and summary.is_travel_advised
        reasons = _explain(summary, ordered[1:]) if is_best and len(ordered) > 1 else []
        ranked.append(
            RankedRoute(summary=summary, rank=index + 1, recommended=recommended, reasons=reasons)
        )
    return ranked


def _explain(best: RouteRiskSummary, others: Sequence[RouteRiskSummary]) -> list[str]:
    """Name the first criterion on which ``best`` beats each other route."""
    reasons: list[str] = []
    best_key = best.sort_key()
    for other in others:
        other_key = other.sort_key()
        for index, (mine, theirs) in enumerate(zip(best_key, other_key, strict=True)):
            if mine < theirs:
                reasons.append(f"{CRITERIA_LABELS[index]} vs. {other.route_id}")
                break
        else:
            reasons.append(f"ties with {other.route_id} on every criterion")
    # Deduplicate while keeping order.
    return list(dict.fromkeys(reasons))
