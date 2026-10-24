from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ("__str__", "order", "issued_at", "total", "efactura_status")
    list_filter = ("efactura_status",)
    search_fields = ("number", "order__number")
