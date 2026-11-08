from django.urls import reverse
from rest_framework import serializers

from .models import Invoice


class InvoiceSummarySerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    is_demo = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = (
            "status",
            "series",
            "number",
            "issued_at",
            "total",
            "efactura_status",
            "pdf_url",
            "is_demo",
        )

    def get_is_demo(self, invoice: Invoice) -> bool:
        return invoice.provider == "demo"

    def get_pdf_url(self, invoice: Invoice) -> str | None:
        if invoice.status != Invoice.Status.ISSUED or not invoice.pdf:
            return None
        return reverse("invoice-pdf", kwargs={"order_number": invoice.order.number})
