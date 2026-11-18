"""Version-specific wire contracts for the consumer migration example."""

from rest_framework import serializers


class OrderV1Serializer(serializers.Serializer):
    id = serializers.IntegerField()
    sku = serializers.CharField()
    total = serializers.CharField()


class OrderV2Serializer(serializers.Serializer):
    id = serializers.IntegerField()
    sku = serializers.CharField()
    total = serializers.DecimalField(max_digits=8, decimal_places=2)
    currency = serializers.CharField()


class OrderV3Serializer(serializers.Serializer):
    id = serializers.IntegerField()
    sku = serializers.CharField()
    total = serializers.DecimalField(max_digits=8, decimal_places=2)
    currency = serializers.CharField()
    fulfillment_state = serializers.ChoiceField(
        choices=("processing", "ready", "shipped")
    )


class AvailabilitySerializer(serializers.Serializer):
    available = serializers.BooleanField()
    checked_at = serializers.DateTimeField()


class LegacyExportSerializer(serializers.Serializer):
    export_id = serializers.CharField()
    format = serializers.ChoiceField(choices=("csv", "json"))


class RiskSummarySerializer(serializers.Serializer):
    risk_level = serializers.ChoiceField(choices=("low", "medium", "high"))
    delayed_orders = serializers.IntegerField()
