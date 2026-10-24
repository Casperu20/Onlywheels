from django.contrib import admin, messages
from rest_framework.exceptions import ValidationError
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from . import services
from .models import Order, OrderItem, OrderStatusChange


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "sku", "description", "unit_price", "quantity", "line_total")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class StatusChangeInline(TabularInline):
    model = OrderStatusChange
    extra = 0
    can_delete = False
    fields = ("created_at", "status", "note", "changed_by")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("number", "created_at", "full_name", "status", "delivery_method", "total", "paid_at")
    list_filter = ("status", "delivery_method", "created_at")
    search_fields = ("number", "email", "full_name", "phone", "items__sku")
    date_hierarchy = "created_at"
    inlines = (OrderItemInline, StatusChangeInline)
    readonly_fields = (
        "number",
        "user",
        "status",
        "delivery_method",
        "subtotal",
        "discount",
        "shipping",
        "fitting",
        "total",
        "vat",
        "voucher",
        "voucher_code",
        "reserved_until",
        "paid_at",
    )
    fieldsets = (
        (None, {"fields": ("number", "user", "status", "delivery_method", "paid_at", "reserved_until")}),
        ("Contact & address", {"fields": ("email", "full_name", "phone", "line1", "line2", "city", "county", "postal_code", "notes")}),
        ("Totals (RON, VAT included)", {"fields": ("subtotal", "discount", "voucher", "voucher_code", "shipping", "fitting", "total", "vat")}),
    )
    actions = ("mark_processing", "mark_shipped", "mark_ready_for_fitting", "mark_completed", "cancel_orders")

    def has_add_permission(self, request):
        return False

    def _transition(self, request, queryset, new_status: str) -> None:
        done, failed = 0, []
        for order in queryset:
            try:
                services.change_status(order, new_status, by=request.user)
                done += 1
            except ValidationError:
                failed.append(order.number)
        if done:
            self.message_user(request, f"{done} order(s) updated to “{new_status}”.", messages.SUCCESS)
        if failed:
            self.message_user(request, f"Not allowed for: {', '.join(failed)}", messages.WARNING)

    @action(description="Mark as processing")
    def mark_processing(self, request, queryset):
        self._transition(request, queryset, Order.Status.PROCESSING)

    @action(description="Mark as shipped (courier)")
    def mark_shipped(self, request, queryset):
        self._transition(request, queryset, Order.Status.SHIPPED)

    @action(description="Mark as ready for fitting (garage)")
    def mark_ready_for_fitting(self, request, queryset):
        self._transition(request, queryset, Order.Status.READY_FOR_FITTING)

    @action(description="Mark as completed")
    def mark_completed(self, request, queryset):
        self._transition(request, queryset, Order.Status.COMPLETED)

    @action(description="Cancel (restock; refund manually in the payment dashboard)")
    def cancel_orders(self, request, queryset):
        self._transition(request, queryset, Order.Status.CANCELLED)
