from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from .models import Invoice
from .serializers import InvoiceSummarySerializer


def _authorized_invoice(user, order_number: str) -> Invoice:
    orders = Order.objects.select_related("invoice").filter(number=order_number)
    if not user.is_staff:
        orders = orders.filter(user=user)
    order = get_object_or_404(orders)
    invoice = getattr(order, "invoice", None)
    if invoice is None:
        raise Http404("Invoice not found.")
    return invoice


class InvoiceDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=InvoiceSummarySerializer)
    def get(self, request, order_number: str):
        invoice = _authorized_invoice(request.user, order_number)
        return Response(InvoiceSummarySerializer(invoice).data)


class InvoicePDFView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={(200, "application/pdf"): OpenApiResponse(OpenApiTypes.BINARY)})
    def get(self, request, order_number: str):
        invoice = _authorized_invoice(request.user, order_number)
        if invoice.status != Invoice.Status.ISSUED or not invoice.pdf:
            raise Http404("Invoice PDF not found.")
        try:
            pdf_file = invoice.pdf.open("rb")
        except FileNotFoundError as exc:
            raise Http404("Invoice PDF not found.") from exc
        filename = f"{invoice.series}-{invoice.number}.pdf"
        return FileResponse(pdf_file, as_attachment=True, filename=filename, content_type="application/pdf")
