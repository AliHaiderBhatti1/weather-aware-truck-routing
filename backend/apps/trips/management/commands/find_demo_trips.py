"""
Scan the next 14 days of forecasts along a set of corridors and print, for
each risk level, the departure windows most likely to show it in the app.

    python manage.py find_demo_trips
    python manage.py find_demo_trips --load 45000 --corridor "Reykjavik, Iceland|Akureyri, Iceland"

Weather is sampled at a handful of points along the straight line between the
endpoints (close enough to the road for picking demo windows), using the same
Open-Meteo client and risk engine as the API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.geo.service import GeoService
from apps.geo.types import GeoPoint
from apps.risk.engine import assess
from apps.risk.levels import RiskLevel
from apps.weather.client import RISK_ONLY_FIELDS
from apps.weather.service import WeatherService

DEFAULT_CORRIDORS = [
    "Denver, CO|Salt Lake City, UT",
    "Cheyenne, WY|Billings, MT",
    "Seattle, WA|Spokane, WA",
    "Orlando, FL|Miami, FL",
    "Amarillo, TX|Albuquerque, NM",
    "Minneapolis, MN|Fargo, ND",
    "Buffalo, NY|Cleveland, OH",
    "Reno, NV|Sacramento, CA",
    "Reykjavik, Iceland|Akureyri, Iceland",
    "Edinburgh, UK|Inverness, UK",
    "Bergen, Norway|Oslo, Norway",
    "Taipei, Taiwan|Kaohsiung, Taiwan",
    "Wellington, New Zealand|Napier, New Zealand",
    "Punta Arenas, Chile|Puerto Natales, Chile",
]
SAMPLES_PER_CORRIDOR = 5
HORIZON_DAYS = 14


class Command(BaseCommand):
    help = "Find corridors and departure windows that currently forecast each risk level."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--load", type=int, default=42_000, help="Load weight in lb")
        parser.add_argument(
            "--corridor",
            action="append",
            dest="corridors",
            help="'Origin|Destination' (repeatable). Defaults to a built-in list.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        load_lb: int = options["load"]
        corridors: list[str] = options["corridors"] or DEFAULT_CORRIDORS
        geo, weather = GeoService(), WeatherService()
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        end = now + timedelta(days=HORIZON_DAYS)

        points: list[GeoPoint] = []
        owners: list[tuple[str, int]] = []
        labels: list[str] = []
        for corridor in corridors:
            try:
                origin_q, dest_q = (part.strip() for part in corridor.split("|", 1))
                origin, dest = geo.resolve(origin_q), geo.resolve(dest_q)
            except Exception as exc:
                self.stderr.write(f"skip {corridor}: {exc}")
                continue
            labels.append(f"{origin.name} -> {dest.name}")
            for i in range(SAMPLES_PER_CORRIDOR):
                t = i / (SAMPLES_PER_CORRIDOR - 1)
                lat = origin.point.lat + (dest.point.lat - origin.point.lat) * t
                lon = origin.point.lon + (dest.point.lon - origin.point.lon) * t
                points.append(GeoPoint(lat, lon))
                owners.append((labels[-1], i))

        series = weather.hourly(points, now, end, fields=RISK_ONLY_FIELDS)

        best: dict[tuple[str, RiskLevel], tuple[datetime, str]] = {}
        for (label, index), hourly in zip(owners, series, strict=True):
            for moment in hourly.times:
                sample = hourly.sample_at(moment)
                if sample is None:
                    continue
                result = assess(sample, load_lb)
                key = (label, result.level)
                detail = (
                    f"sample {index + 1}/{SAMPLES_PER_CORRIDOR} wind={sample.wind_mph:.0f} mph "
                    f"rain={sample.rain_in_per_hr:.2f} snow={sample.snow_in_per_hr:.2f} in/hr"
                    + (f" [{result.applied_rule}]" if result.applied_rule else "")
                )
                if key not in best or moment < best[key][0]:
                    best[key] = (moment, detail)

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Load {load_lb:,} lb · scanned {len(points)} points")
        )
        for level in (RiskLevel.NO_TRAVEL, RiskLevel.SEVERE, RiskLevel.HIGH, RiskLevel.MODERATE):
            hits = sorted(
                (
                    (label, when, detail)
                    for (label, lvl), (when, detail) in best.items()
                    if lvl == level
                ),
                key=lambda item: item[1],
            )
            self.stdout.write(self.style.SUCCESS(f"\n{level.label}: {len(hits)} corridor(s)"))
            for label, when, detail in hits:
                depart = when - timedelta(hours=2)
                self.stdout.write(
                    f"  {label:45} first at {when:%a %b %d %H:%M}Z  "
                    f"-> depart ~{depart:%a %b %d %H:%M}Z   ({detail})"
                )
        self.stdout.write(
            "\nTimes are UTC; departure suggestions put the truck mid-route at the forecast hour."
        )
