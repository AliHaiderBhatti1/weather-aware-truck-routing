from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

CHECKPOINT_INTERVALS = (10, 25, 50)
MAX_LOAD_LB = 200_000
PAST_DEPARTURE_GRACE = timedelta(hours=1)


class PlaceInputSerializer(serializers.Serializer[dict[str, Any]]):
    """Either a free-text query to geocode, or explicit coordinates (plus a display name)."""

    query = serializers.CharField(required=False, max_length=200, trim_whitespace=True)
    name = serializers.CharField(required=False, max_length=200, trim_whitespace=True)
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(required=False, min_value=-180, max_value=180)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        has_coords = "lat" in attrs and "lon" in attrs
        if not has_coords and not attrs.get("query"):
            raise serializers.ValidationError("Provide either 'query' or both 'lat' and 'lon'.")
        if ("lat" in attrs) != ("lon" in attrs):
            raise serializers.ValidationError("'lat' and 'lon' must be provided together.")
        return attrs


class TripPlanRequestSerializer(serializers.Serializer[dict[str, Any]]):
    origin = PlaceInputSerializer()
    destination = PlaceInputSerializer()
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.IntegerField(min_value=0, max_value=MAX_LOAD_LB)
    checkpoint_interval_miles = serializers.ChoiceField(choices=CHECKPOINT_INTERVALS, default=25)

    def validate_departure_time(self, value: Any) -> Any:
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_default_timezone())
        now = timezone.now()
        if value < now - PAST_DEPARTURE_GRACE:
            raise serializers.ValidationError("Departure time cannot be in the past.")
        if value > now + timedelta(days=settings.MAX_DEPARTURE_DAYS_AHEAD):
            raise serializers.ValidationError(
                f"Forecasts are only available {settings.MAX_DEPARTURE_DAYS_AHEAD} days ahead."
            )
        return value
