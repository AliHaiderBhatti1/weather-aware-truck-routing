"""Unit conversions. Upstream APIs speak metres/seconds; the brief speaks miles/mph/inches."""

from __future__ import annotations

METERS_PER_MILE = 1609.344
KM_PER_MILE = 1.609344
MM_PER_INCH = 25.4
CM_PER_INCH = 2.54


def meters_to_miles(meters: float) -> float:
    return meters / METERS_PER_MILE


def miles_to_meters(miles: float) -> float:
    return miles * METERS_PER_MILE


def kmh_to_mph(kmh: float) -> float:
    return kmh / KM_PER_MILE


def mm_to_inches(mm: float) -> float:
    return mm / MM_PER_INCH


def cm_to_inches(cm: float) -> float:
    return cm / CM_PER_INCH


def celsius_to_fahrenheit(celsius: float) -> float:
    return celsius * 9 / 5 + 32
