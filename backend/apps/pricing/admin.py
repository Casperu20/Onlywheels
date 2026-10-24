from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from .models import Voucher


@admin.register(Voucher)
class VoucherAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = (
        "code",
        "kind",
        "value",
        "min_order_total",
        "valid_until",
        "used_count",
        "max_uses",
        "is_active",
    )
    list_filter = ("kind", "is_active")
    search_fields = ("code", "description")
    readonly_fields = ("used_count",)
