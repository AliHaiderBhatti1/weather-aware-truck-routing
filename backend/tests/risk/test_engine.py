import pytest

from apps.risk.engine import (
    RiskFactor,
    WeatherSample,
    apply_load_rules,
    assess,
    classify_rain,
    classify_snow,
    classify_wind,
)
from apps.risk.levels import RiskLevel

LOW, MOD, HIGH, SEV, STOP = RiskLevel


@pytest.mark.parametrize(
    ("mph", "expected"),
    [
        (0, LOW),
        (24.9, LOW),
        (25, MOD),
        (34.9, MOD),
        (35, HIGH),
        (44.9, HIGH),
        (45, SEV),
        (54.9, SEV),
        (55, STOP),
        (90, STOP),
    ],
)
def test_wind_thresholds(mph: float, expected: RiskLevel) -> None:
    assert classify_wind(mph) is expected


@pytest.mark.parametrize(
    ("inches", "expected"),
    [
        (0.0, LOW),
        (0.099, LOW),
        (0.10, MOD),
        (0.249, MOD),
        (0.25, HIGH),
        (0.499, HIGH),
        (0.50, SEV),
        (1.00, SEV),  # brief: 0.50-1.00 is Severe, > 1.00 is No Travel
        (1.001, STOP),
    ],
)
def test_rain_thresholds(inches: float, expected: RiskLevel) -> None:
    assert classify_rain(inches) is expected


@pytest.mark.parametrize(
    ("inches", "expected"),
    [
        (0.0, LOW),
        (0.49, LOW),
        (0.5, MOD),
        (0.99, MOD),
        (1.0, HIGH),
        (1.99, HIGH),
        (2.0, SEV),
        (3.0, SEV),  # brief: 2.0-3.0 is Severe, > 3.0 is No Travel
        (3.01, STOP),
    ],
)
def test_snow_thresholds(inches: float, expected: RiskLevel) -> None:
    assert classify_snow(inches) is expected


def test_negative_readings_are_treated_as_zero() -> None:
    assert classify_rain(-0.5) is LOW
    assert classify_wind(-1) is LOW


@pytest.mark.parametrize(
    ("mph", "load", "expected"),
    [
        (55, 0, STOP),  # >= 55 mph: any load
        (60, 80_000, STOP),
        (45, 30_000, None),  # 45-54 needs > 30k
        (45, 30_001, STOP),
        (54.9, 35_000, STOP),
        (35, 40_000, None),  # 35-44 needs > 40k
        (35, 40_001, SEV),
        (44.9, 45_000, SEV),
        (34.9, 80_000, None),  # below 35 mph load never matters
        (10, 80_000, None),
    ],
)
def test_load_rules(mph: float, load: float, expected: RiskLevel | None) -> None:
    level, rule = apply_load_rules(mph, load)
    assert level is expected
    assert (rule is not None) is (expected is not None)


def test_overall_level_is_the_worst_component() -> None:
    sample = WeatherSample(wind_mph=10, rain_in_per_hr=0.3, snow_in_per_hr=0.0)
    result = assess(sample, load_lb=10_000)
    assert result.level is HIGH
    assert result.dominant_factor is RiskFactor.RAIN
    assert result.applied_rule is None


def test_clear_weather_has_no_dominant_factor() -> None:
    result = assess(WeatherSample(wind_mph=5, rain_in_per_hr=0, snow_in_per_hr=0), 10_000)
    assert result.level is LOW
    assert result.dominant_factor is RiskFactor.NONE


def test_load_rule_escalates_high_wind_to_severe_for_heavy_truck() -> None:
    sample = WeatherSample(wind_mph=40, rain_in_per_hr=0.0, snow_in_per_hr=0.0)

    light = assess(sample, load_lb=20_000)
    heavy = assess(sample, load_lb=44_000)

    assert light.level is HIGH
    assert light.dominant_factor is RiskFactor.WIND
    assert heavy.level is SEV
    assert heavy.dominant_factor is RiskFactor.LOAD
    assert heavy.applied_rule is not None and "40,000" in heavy.applied_rule


def test_load_rule_does_not_lower_a_worse_weather_level() -> None:
    # Wind says Severe via load rule, but snow already says No Travel.
    sample = WeatherSample(wind_mph=40, rain_in_per_hr=0.0, snow_in_per_hr=3.5)
    result = assess(sample, load_lb=50_000)
    assert result.level is STOP
    assert result.dominant_factor is RiskFactor.SNOW


def test_wind_at_or_above_55_explains_rule_even_without_load() -> None:
    result = assess(WeatherSample(wind_mph=58, rain_in_per_hr=0, snow_in_per_hr=0), 1_000)
    assert result.level is STOP
    assert result.dominant_factor is RiskFactor.WIND
    assert result.applied_rule is not None and "55" in result.applied_rule
