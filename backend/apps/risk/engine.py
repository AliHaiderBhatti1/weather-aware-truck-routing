"""
Weather risk engine.

Pure functions over plain dataclasses so the rules are trivially unit-testable
and reusable outside Django (CLI, notebooks, future workers).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from apps.risk import thresholds
from apps.risk.levels import RiskLevel


class RiskFactor(StrEnum):
    WIND = "wind"
    RAIN = "rain"
    SNOW = "snow"
    LOAD = "load"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class WeatherSample:
    """Weather at a single place and time, already in the brief's units."""

    wind_mph: float
    rain_in_per_hr: float
    snow_in_per_hr: float
    wind_gust_mph: float | None = None
    temperature_f: float | None = None
    weather_code: int | None = None


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    wind_level: RiskLevel
    rain_level: RiskLevel
    snow_level: RiskLevel
    dominant_factor: RiskFactor
    applied_rule: str | None
    """Human readable description of the load rule that escalated the level, if any."""


def classify_wind(wind_mph: float) -> RiskLevel:
    return thresholds.classify(wind_mph, thresholds.WIND_MPH)


def classify_rain(rain_in_per_hr: float) -> RiskLevel:
    return thresholds.classify(rain_in_per_hr, thresholds.RAIN_IN_PER_HR)


def classify_snow(snow_in_per_hr: float) -> RiskLevel:
    return thresholds.classify(snow_in_per_hr, thresholds.SNOW_IN_PER_HR)


def apply_load_rules(wind_mph: float, load_lb: float) -> tuple[RiskLevel | None, str | None]:
    """
    Return the level forced by the load rules for this wind speed, or ``None``.

    Rules from the brief:
      * >= 55 mph           -> No Travel for any load
      * 45-54 mph + >30k lb -> No Travel
      * 35-44 mph + >40k lb -> Severe
    """
    if wind_mph >= thresholds.NO_TRAVEL_WIND_MPH:
        return RiskLevel.NO_TRAVEL, "Wind >= 55 mph: no travel for any load"
    if wind_mph >= thresholds.HEAVY_LOAD_NO_TRAVEL_WIND_MPH:
        if load_lb > thresholds.HEAVY_LOAD_NO_TRAVEL_LB:
            return RiskLevel.NO_TRAVEL, "Wind 45-54 mph with load > 30,000 lb: no travel"
        return None, None
    if (
        wind_mph >= thresholds.HEAVY_LOAD_SEVERE_WIND_MPH
        and load_lb > thresholds.HEAVY_LOAD_SEVERE_LB
    ):
        return RiskLevel.SEVERE, "Wind 35-44 mph with load > 40,000 lb: severe"
    return None, None


def assess(sample: WeatherSample, load_lb: float) -> RiskAssessment:
    """Classify a weather sample for a truck carrying ``load_lb`` pounds."""
    wind_level = classify_wind(sample.wind_mph)
    rain_level = classify_rain(sample.rain_in_per_hr)
    snow_level = classify_snow(sample.snow_in_per_hr)

    weather_level = max(wind_level, rain_level, snow_level)
    load_level, applied_rule = apply_load_rules(sample.wind_mph, load_lb)

    if load_level is not None and load_level > weather_level:
        return RiskAssessment(
            level=load_level,
            wind_level=wind_level,
            rain_level=rain_level,
            snow_level=snow_level,
            dominant_factor=RiskFactor.LOAD,
            applied_rule=applied_rule,
        )

    # The rule may coincide with the weather level (e.g. wind alone already
    # says No Travel). Keep the explanation but attribute to the weather factor.
    if weather_level == RiskLevel.LOW:
        dominant = RiskFactor.NONE
    elif wind_level == weather_level:
        dominant = RiskFactor.WIND
    elif rain_level == weather_level:
        dominant = RiskFactor.RAIN
    else:
        dominant = RiskFactor.SNOW

    return RiskAssessment(
        level=weather_level,
        wind_level=wind_level,
        rain_level=rain_level,
        snow_level=snow_level,
        dominant_factor=dominant,
        applied_rule=applied_rule if load_level == weather_level else None,
    )
