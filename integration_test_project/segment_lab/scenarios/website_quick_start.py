# isort: skip_file
from django_api_versioning import endpoint
from rest_framework.views import APIView
from rest_framework.response import Response


@endpoint("invoices/<int:invoice_id>/", version=2, view_name="invoice-detail")
class InvoiceDetailView(APIView):
    def get(self, request, invoice_id):
        return Response({"id": invoice_id, "status": "paid"})
