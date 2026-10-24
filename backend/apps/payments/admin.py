from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ("created_at", "order", "provider", "amount", "status", "payment_reference")
    list_filter = ("provider", "status")
    search_fields = ("order__number", "session_id", "payment_reference")
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(WebhookEvent)
class WebhookEventAdmin(ModelAdmin):
    list_display = ("created_at", "provider", "type", "event_id")
    list_filter = ("provider", "type")
    search_fields = ("event_id",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
