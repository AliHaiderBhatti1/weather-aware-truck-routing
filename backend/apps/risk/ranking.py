"""
Route scoring and recommendation.

The brief's preference order is applied lexicographically:
    1. fewest Severe miles
    2. fewest High miles
    3. lowest average risk
    4. shortest travel time

``NO_TRAVEL`` is not in that ladder, so we treat it as a hard constraint that
sorts above everything else: any No-Travel checkpoint pushes a route to the
bottom and disqualifies it from being recommended.

Checkpoints without a forecast are *unknown*, never assumed calm. Their miles
are tracked separately and excluded from the average, and a route where more
than ``MAX_UNKNOWN_SHARE`` of the miles are unknown ranks below fully assessed
routes and is not recommended, since gaps could hide Severe weather.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from apps.risk.levels import RiskLevel

MAX_UNKNOWN_SHARE = 0.25


@dataclass(frozen=True, slots=True)
class RiskSegment:
    """A stretch of road represented by one checkpoint's assessment."""

    level: RiskLevel | None
    """``None`` when the checkpoint had no forecast."""
    miles: float


@dataclass(frozen=True, slots=True)
class RouteRiskSummary:
    route_id: str
    duration_seconds: float
    total_miles: float
    miles_by_level: dict[RiskLevel, float]
    average_risk: float
    """Distance-weighted mean of the numeric level (0 = Low ... 4 = No Travel), known miles only."""
    max_level: RiskLevel
    """Worst level at any checkpoint, including zero-length ones."""
    unknown_miles: float = 0.0
    """Miles represented by checkpoints without a forecast."""

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
    def unknown_share(self) -> float:
        assessed = self.total_miles + self.unknown_miles
        return self.unknown_miles / assessed if assessed else 1.0

    @property
    def is_sufficiently_forecast(self) -> bool:
        return self.unknown_share <= MAX_UNKNOWN_SHARE

    @property
    def is_travel_advised(self) -> bool:
        # Checked on the worst checkpoint, not just mileage, so a No-Travel
        # point can never be outweighed by its length.
        return self.max_level < RiskLevel.NO_TRAVEL

    def sort_key(self) -> tuple[int, float, int, float, float, float, float]:
        """Lexicographic ranking key; lower is better. Aligned with ``CRITERIA_LABELS``."""
        # Round so that floating point noise never decides a tie.
        return (
            0 if self.is_travel_advised else 1,
            round(self.no_travel_miles, 1),
            0 if self.is_sufficiently_forecast else 1,
            round(self.severe_miles, 1),
            round(self.high_miles, 1),
            round(self.average_risk, 2),
            round(self.duration_seconds),
        )


CRITERIA_LABELS: Sequence[str] = (
    "no No-Travel conditions",
    "fewer No-Travel miles",
    "forecast available for the whole route",
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
    unknown = 0.0
    max_level = RiskLevel.LOW
    for segment in segments:
        if segment.level is None:
            unknown += max(segment.miles, 0.0)
            continue
        max_level = max(max_level, segment.level)
        if segment.miles <= 0:
            continue
        miles_by_level[segment.level] += segment.miles
        weighted += int(segment.level) * segment.miles
        total += segment.miles
    average = weighted / total if total else 0.0
    return RouteRiskSummary(
        route_id=route_id,
        duration_seconds=duration_seconds,
        total_miles=total,
        miles_by_level=miles_by_level,
        average_risk=average,
        max_level=max_level,
        unknown_miles=unknown,
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
    """Sort routes best-first and mark the recommended one, if any is safe and forecast."""
    ordered = sorted(summaries, key=lambda summary: summary.sort_key())
    ranked: list[RankedRoute] = []
    for index, summary in enumerate(ordered):
        is_best = index == 0
        recommended = is_best and summary.is_travel_advised and summary.is_sufficiently_forecast
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
