"""
"drf_viewset_class": @endpoint applied directly to a ViewSet class.
"""
from rest_framework import viewsets
from rest_framework.response import Response

from django_api_versioning import endpoint


@endpoint("receipts/", version=1, view_name="receipt-list")
class ReceiptViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"handler": "ReceiptViewSet.list"})