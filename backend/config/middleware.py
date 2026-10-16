"""Infrastructure middleware."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

HEALTH_PATH = "/api/health/"


def health_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": settings.SPECTACULAR_SETTINGS["VERSION"],
        "providers": {
            "routing": "mapbox" if settings.MAPBOX_ACCESS_TOKEN else "unconfigured",
            "weather": "open-meteo",
        },
    }


class HealthCheckMiddleware:
    """
    Answer the liveness probe before host validation.

    Hosting platforms probe containers with internal IPs or ports as the Host
    header, which ALLOWED_HOSTS would reject with a 400 and fail the deploy.
    Placed after CorsMiddleware so browser calls still receive CORS headers.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == HEALTH_PATH and request.method in {"GET", "HEAD"}:
            return JsonResponse(health_payload())
        return self.get_response(request)
