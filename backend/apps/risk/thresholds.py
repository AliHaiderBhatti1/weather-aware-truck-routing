"""
Weather thresholds from the assessment brief, expressed as data so the same
table drives the engine, the tests and the documentation.

Each band is ``(lower_bound_inclusive, level)``. A reading is classified by the
last band whose lower bound it meets. Bounds for ``NO_TRAVEL`` follow the brief
literally: wind uses ``>= 55`` while rain and snow use strict ``>`` (1.00 and
3.00 in/hr are still *Severe*).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from apps.risk.levels import RiskLevel


@dataclass(frozen=True, slots=True)
class Band:
    lower: float
    level: RiskLevel
    lower_exclusive: bool = False

    def contains(self, value: float) -> bool:
        return value > self.lower if self.lower_exclusive else value >= self.lower


WIND_MPH: Final[tuple[Band, ...]] = (
    Band(0.0, RiskLevel.LOW),
    Band(25.0, RiskLevel.MODERATE),
    Band(35.0, RiskLevel.HIGH),
    Band(45.0, RiskLevel.SEVERE),
    Band(55.0, RiskLevel.NO_TRAVEL),
)

RAIN_IN_PER_HR: Final[tuple[Band, ...]] = (
    Band(0.0, RiskLevel.LOW),
    Band(0.10, RiskLevel.MODERATE),
    Band(0.25, RiskLevel.HIGH),
    Band(0.50, RiskLevel.SEVERE),
    Band(1.00, RiskLevel.NO_TRAVEL, lower_exclusive=True),
)

SNOW_IN_PER_HR: Final[tuple[Band, ...]] = (
    Band(0.0, RiskLevel.LOW),
    Band(0.5, RiskLevel.MODERATE),
    Band(1.0, RiskLevel.HIGH),
    Band(2.0, RiskLevel.SEVERE),
    Band(3.0, RiskLevel.NO_TRAVEL, lower_exclusive=True),
)

# Load rules (wind band -> load threshold in lb -> escalated level)
NO_TRAVEL_WIND_MPH: Final = 55.0
HEAVY_LOAD_NO_TRAVEL_WIND_MPH: Final = 45.0  # 45-54 mph
HEAVY_LOAD_NO_TRAVEL_LB: Final = 30_000  # strictly greater than
HEAVY_LOAD_SEVERE_WIND_MPH: Final = 35.0  # 35-44 mph
HEAVY_LOAD_SEVERE_LB: Final = 40_000  # strictly greater than


def classify(value: float, bands: tuple[Band, ...]) -> RiskLevel:
    """Return the level of the highest band that ``value`` falls into."""
    if value < 0:
        value = 0.0
    level = bands[0].level
    for band in bands:
        if band.contains(value):
            level = band.level
    return level
