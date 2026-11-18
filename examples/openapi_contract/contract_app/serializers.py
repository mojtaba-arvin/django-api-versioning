from rest_framework import serializers


class ProductV1Serializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    price = serializers.CharField()


class ProductV2Serializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()


class AvailabilitySerializer(serializers.Serializer):
    available = serializers.BooleanField()
    checked_at = serializers.DateTimeField()
