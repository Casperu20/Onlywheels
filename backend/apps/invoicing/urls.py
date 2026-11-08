from django.urls import path

from .views import InvoiceDetailView, InvoicePDFView

urlpatterns = [
    path("<str:order_number>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("<str:order_number>/pdf/", InvoicePDFView.as_view(), name="invoice-pdf"),
]
