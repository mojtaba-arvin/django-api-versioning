from datetime import datetime, timezone
from decimal import Decimal

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import (
    AvailabilitySerializer,
    ProductV1Serializer,
    ProductV2Serializer,
)


class ProductViewSetV1(viewsets.GenericViewSet):
    """V1 implementation and custom action inherited by V2."""

    queryset = []
    serializer_class = ProductV1Serializer

    @extend_schema(responses=ProductV1Serializer(many=True))
    def list(self, request, *args, **kwargs):
        payload = [{"id": 1, "name": "Desk lamp", "price": "12.50"}]
        return Response(self.get_serializer(payload, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("id", int, OpenApiParameter.PATH)],
        responses=ProductV1Serializer,
    )
    def retrieve(self, request, pk: int | None = None, *args, **kwargs):
        payload = {"id": int(pk or 1), "name": "Desk lamp", "price": "12.50"}
        return Response(self.get_serializer(payload).data)

    @extend_schema(responses=AvailabilitySerializer)
    @action(detail=False, methods=["get"], url_path="legacy/export")
    def legacy_export(self, request, *args, **kwargs):
        payload = {
            "available": True,
            "checked_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        return Response(AvailabilitySerializer(payload).data)

    @extend_schema(responses=AvailabilitySerializer)
    @action(detail=False, methods=["get"])
    def availability(self, request, *args, **kwargs):
        payload = {
            "available": True,
            "checked_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        return Response(AvailabilitySerializer(payload).data)


class ProductViewSetV2(viewsets.GenericViewSet):
    """V2 replaces list/detail but intentionally omits availability."""

    queryset = []
    serializer_class = ProductV2Serializer

    @extend_schema(responses=ProductV2Serializer(many=True))
    def list(self, request, *args, **kwargs):
        payload = [
            {
                "id": 1,
                "name": "Desk lamp",
                "price": Decimal("12.50"),
                "currency": "USD",
            }
        ]
        return Response(self.get_serializer(payload, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("id", int, OpenApiParameter.PATH)],
        responses=ProductV2Serializer,
    )
    def retrieve(self, request, pk=None, *args, **kwargs):
        payload = {
            "id": int(pk or 1),
            "name": "Desk lamp",
            "price": Decimal("12.50"),
            "currency": "USD",
        }
        return Response(self.get_serializer(payload).data)
