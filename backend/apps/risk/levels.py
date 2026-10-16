"""Risk level vocabulary shared by the engine, the API and the frontend."""

from __future__ import annotations

from enum import IntEnum


class RiskLevel(IntEnum):
    """Ordered severity. Higher is worse; ``NO_TRAVEL`` is a hard stop."""

    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def slug(self) -> str:
        return self.name.lower()

    @property
    def label(self) -> str:
        return {
            RiskLevel.LOW: "Low",
            RiskLevel.MODERATE: "Moderate",
            RiskLevel.HIGH: "High",
            RiskLevel.SEVERE: "Severe",
            RiskLevel.NO_TRAVEL: "No Travel",
        }[self]
