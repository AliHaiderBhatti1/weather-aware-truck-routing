from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.geo.serializers import GeocodeQuerySerializer, PlaceSerializer
from apps.geo.service import GeoService


class GeocodeView(APIView):
    """Forward geocoding with autocomplete, proxied so the Mapbox token stays server-side."""

    @extend_schema(parameters=[GeocodeQuerySerializer], responses={200: PlaceSerializer(many=True)})
    def get(self, request: Request) -> Response:
        params = GeocodeQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        places = GeoService().search(
            params.validated_data["q"], limit=params.validated_data["limit"]
        )
        payload = [
            {
                "name": place.name,
                "full_name": place.full_name,
                "lat": place.point.lat,
                "lon": place.point.lon,
                "kind": place.kind,
            }
            for place in places
        ]
        return Response(PlaceSerializer(payload, many=True).data)  # type: ignore[arg-type]
