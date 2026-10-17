from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trips.models import TripPlan
from apps.trips.serializers import TripPlanRequestSerializer
from apps.trips.services.heatmap import build_heatmap
from apps.trips.services.planner import PlanRequest, TripPlanner
from apps.trips.services.timing import StageTimer
from config.middleware import health_payload


class HealthView(APIView):
    """Liveness probe used by hosting health checks and the frontend's warm-up indicator."""

    throttle_classes: list[type] = []

    @extend_schema(responses={200: {"type": "object"}})
    def get(self, request: Request) -> Response:
        # Normally answered by config.middleware.HealthCheckMiddleware; kept so
        # the endpoint appears in the OpenAPI schema.
        return Response(health_payload())


def _plan_payload(plan: TripPlan) -> dict[str, Any]:
    return {"id": str(plan.id), "created_at": plan.created_at.isoformat(), **plan.result}


class TripPlanCreateView(APIView):
    """Plan a trip: 3 routes, weather at every checkpoint, risk and a recommendation."""

    @extend_schema(
        request=TripPlanRequestSerializer,
        responses={201: OpenApiResponse(description="The computed trip plan")},
    )
    def post(self, request: Request) -> Response:
        serializer = TripPlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        timer = StageTimer()
        planner = TripPlanner()
        with timer.stage("geocode"), ThreadPoolExecutor(max_workers=2) as pool:
            origin, destination = pool.map(
                planner.resolve_place, (data["origin"], data["destination"])
            )
            plan_request = PlanRequest(
                origin=origin,
                destination=destination,
                departure=data["departure_time"].replace(microsecond=0),
                load_lb=data["load_weight_lb"],
                interval_miles=data["checkpoint_interval_miles"],
            )
        result = planner.plan(plan_request, timer=timer)
        with timer.stage("persist"):
            plan = TripPlan.objects.create(request=result["request"], result=result)
        response = Response(_plan_payload(plan), status=status.HTTP_201_CREATED)
        response["Server-Timing"] = timer.header()
        return response


class TripPlanDetailView(APIView):
    @extend_schema(responses={200: OpenApiResponse(description="A previously computed plan")})
    def get(self, request: Request, plan_id: str) -> Response:
        plan = get_object_or_404(TripPlan, pk=plan_id)
        return Response(_plan_payload(plan))


class TripPlanHeatmapView(APIView):
    """0-48 h corridor heatmap for a plan, computed on first request and stored."""

    @extend_schema(responses={200: OpenApiResponse(description="Hourly risk grid")})
    def get(self, request: Request, plan_id: str) -> Response:
        plan = get_object_or_404(TripPlan, pk=plan_id)
        if plan.heatmap is not None:
            return Response(plan.heatmap)
        heatmap = build_heatmap(plan.result)
        if heatmap.get("complete", True):
            plan.heatmap = heatmap
            plan.save(update_fields=["heatmap"])
        return Response(heatmap)
