"""
Domain exceptions and the DRF exception handler that maps them to HTTP responses.

Every error returned by the API has the same JSON shape::

    {"error": {"code": "upstream_error", "message": "...", "details": {...}}}
"""

from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Base class for errors we expect and want to surface to API clients."""

    code: str = "error"
    http_status: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class GeocodingError(DomainError):
    code = "geocoding_failed"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class RoutingError(DomainError):
    code = "routing_failed"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class UpstreamError(DomainError):
    code = "upstream_error"
    http_status = status.HTTP_502_BAD_GATEWAY


class ConfigurationError(DomainError):
    code = "configuration_error"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


def _error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        if exc.http_status >= 500:
            logger.warning("%s: %s %s", exc.code, exc.message, exc.details)
        return Response(_error_payload(exc.code, exc.message, exc.details), status=exc.http_status)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        message = str(data["detail"])
        details = None
    elif isinstance(data, dict):
        message = "Request validation failed."
        details = data
    else:
        message = "Request failed."
        details = data
    code = getattr(exc, "default_code", "error")
    response.data = _error_payload(str(code), message, details)
    return response
