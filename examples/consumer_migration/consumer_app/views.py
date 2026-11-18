"""Three successive Order API contracts with inherited and removed actions."""

from datetime import datetime, timezone
from decimal import Decimal

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import (
    AvailabilitySerializer,
    LegacyExportSerializer,
    OrderV1Serializer,
    OrderV2Serializer,
    OrderV3Serializer,
    RiskSummarySerializer,
)


class OrderViewSetV1(viewsets.GenericViewSet):
    """Original V1 contract, including the legacy export action."""

    queryset = []
    serializer_class = OrderV1Serializer

    @extend_schema(responses=OrderV1Serializer(many=True))
    def list(self, request):
        payload = [{"id": 101, "sku": "LAMP-01", "total": "19.95"}]
        return Response(self.get_serializer(payload, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("id", int, OpenApiParameter.PATH)],
        responses=OrderV1Serializer,
    )
    def retrieve(self, request, pk: int | None = None):
        payload = {"id": int(pk or 101), "sku": "LAMP-01", "total": "19.95"}
        return Response(self.get_serializer(payload).data)

    @extend_schema(responses=AvailabilitySerializer)
    @action(detail=False, methods=["get"])
    def availability(self, request):
        payload = {
            "available": True,
            "checked_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        return Response(AvailabilitySerializer(payload).data)

    @extend_schema(responses=LegacyExportSerializer)
    @action(detail=False, methods=["get"], url_path="legacy/export")
    def legacy_export(self, request):
        return Response({"export_id": "exp-101", "format": "csv"})


class OrderViewSetV2(viewsets.GenericViewSet):
    """V2 replaces list/detail while inheriting V1's availability and export."""

    queryset = []
    serializer_class = OrderV2Serializer

    @extend_schema(responses=OrderV2Serializer(many=True))
    def list(self, request):
        payload = [
            {
                "id": 101,
                "sku": "LAMP-01",
                "total": Decimal("19.95"),
                "currency": "USD",
            }
        ]
        return Response(self.get_serializer(payload, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("id", int, OpenApiParameter.PATH)],
        responses=OrderV2Serializer,
    )
    def retrieve(self, request, pk: int | None = None):
        payload = {
            "id": int(pk or 101),
            "sku": "LAMP-01",
            "total": Decimal("19.95"),
            "currency": "USD",
        }
        return Response(self.get_serializer(payload).data)


class OrderViewSetV3(viewsets.GenericViewSet):
    """V3 evolves the response and adds a new action; availability is inherited."""

    queryset = []
    serializer_class = OrderV3Serializer

    @extend_schema(responses=OrderV3Serializer(many=True))
    def list(self, request):
        payload = [
            {
                "id": 101,
                "sku": "LAMP-01",
                "total": Decimal("19.95"),
                "currency": "USD",
                "fulfillment_state": "ready",
            }
        ]
        return Response(self.get_serializer(payload, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("id", int, OpenApiParameter.PATH)],
        responses=OrderV3Serializer,
    )
    def retrieve(self, request, pk: int | None = None):
        payload = {
            "id": int(pk or 101),
            "sku": "LAMP-01",
            "total": Decimal("19.95"),
            "currency": "USD",
            "fulfillment_state": "ready",
        }
        return Response(self.get_serializer(payload).data)

    @extend_schema(responses=RiskSummarySerializer)
    @action(detail=False, methods=["get"], url_path="risk-summary")
    def risk_summary(self, request):
        return Response({"risk_level": "low", "delayed_orders": 0})
