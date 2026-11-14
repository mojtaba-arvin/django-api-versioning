"""
"drf_*" scenarios: DRF views registered through @endpoint.

The same module is imported under three REST_FRAMEWORK configurations
(see lab/scenarios.py). Every view reports what DRF sees at request time.
"""

from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from django_api_versioning import endpoint


def describe(request, handler):
    return {
        "handler": handler,
        "request.version": request.version,
        "request.versioning_scheme": (
            type(request.versioning_scheme).__name__
            if request.versioning_scheme
            else None
        ),
        "resolver_match.route": request.resolver_match.route,
        "resolver_match.kwargs": request.resolver_match.kwargs,
    }


@endpoint("invoices/", version=1, view_name="invoice-list")
class InvoiceListV1(APIView):
    def get(self, request):
        return Response(describe(request, "InvoiceListV1.get"))


@endpoint("invoices/", version=3, view_name="invoice-list")
class InvoiceListV3(APIView):
    def get(self, request):
        return Response(describe(request, "InvoiceListV3.get"))


@endpoint("ping/", version=1, view_name="ping")
@api_view(["GET"])
def ping(request):
    return Response(describe(request, "ping"))


class ReceiptViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response(describe(request, "ReceiptViewSet.list"))

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(describe(request, "ReceiptViewSet.summary"))


# A ViewSet can only be registered as a configured callable: the action map
# is supplied by the caller, and @action routes are not generated.
endpoint("receipts/", version=2, view_name="receipt-list")(
    ReceiptViewSet.as_view({"get": "list"})
)
