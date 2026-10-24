from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Shipment


@admin.register(Shipment)
class ShipmentAdmin(ModelAdmin):
    list_display = ("order", "carrier", "awb", "status", "created_at")
    list_filter = ("carrier", "status")
    search_fields = ("awb", "order__number")
