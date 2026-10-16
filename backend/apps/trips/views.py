from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness probe used by hosting health checks and the frontend's warm-up indicator."""

    throttle_classes: list[type] = []

    @extend_schema(responses={200: {"type": "object"}})
    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "version": settings.SPECTACULAR_SETTINGS["VERSION"],
                "providers": {
                    "routing": "mapbox" if settings.MAPBOX_ACCESS_TOKEN else "unconfigured",
                    "weather": "open-meteo",
                },
            }
        )
