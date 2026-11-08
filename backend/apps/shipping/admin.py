from django.contrib import admin, messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from . import services
from .models import Shipment


@admin.register(Shipment)
class ShipmentAdmin(ModelAdmin):
    actions = ("retry_failed", "retry_confirmed_absent", "adopt_manual_awb", "fetch_labels", "refresh_tracking")
    list_display = ("order", "carrier", "awb", "status", "carrier_status", "attempt_count", "label_link", "created_at")
    list_filter = ("carrier", "status")
    search_fields = ("awb", "order__number")
    list_select_related = ("order",)
    readonly_fields = (
        "order",
        "carrier",
        "status",
        "carrier_status",
        "parcels",
        "weight_kg",
        "tracking_url",
        "label_link",
        "last_error",
        "attempt_count",
        "last_attempted_at",
        "last_tracked_at",
    )
    fields = ("awb", *readonly_fields)

    def get_urls(self):
        return [
            path(
                "<path:object_id>/label/",
                self.admin_site.admin_view(self.label_view),
                name="shipping_shipment_label",
            ),
            *super().get_urls(),
        ]

    def label_view(self, request, object_id):
        if not self.has_view_permission(request):
            raise Http404
        shipment = get_object_or_404(Shipment, pk=object_id)
        if not shipment.label_pdf:
            raise Http404("No label stored for this shipment.")
        return FileResponse(
            shipment.label_pdf.open("rb"),
            content_type="application/pdf",
            filename=f"awb-{shipment.awb}.pdf",
        )

    @admin.display(description="Label")
    def label_link(self, shipment: Shipment):
        if not shipment.label_pdf:
            return "—"
        return format_html('<a href="{}">PDF</a>', reverse("admin:shipping_shipment_label", args=[shipment.pk]))

    def _run(self, request, queryset, action, verb):
        done, errors = 0, []
        for shipment in queryset.select_related("order"):
            try:
                action(shipment)
                done += 1
            except services.ShipmentStateError as exc:
                errors.append(f"{shipment.order.number}: {exc}")
        self.message_user(request, f"{verb} {done} shipment(s).", level=messages.SUCCESS)
        for error in errors:
            self.message_user(request, error, level=messages.WARNING)

    @admin.action(description="Retry failed AWB creation")
    def retry_failed(self, request, queryset):
        self._run(request, queryset, services.retry_shipment, "Retried")

    @admin.action(description="Retry after confirming in the carrier portal that no AWB exists")
    def retry_confirmed_absent(self, request, queryset):
        self._run(request, queryset, lambda s: services.retry_shipment(s, confirmed_absent=True), "Retried")

    @admin.action(description="Use the AWB entered manually (marks the order shipped)")
    def adopt_manual_awb(self, request, queryset):
        self._run(request, queryset, services.adopt_manual_awb, "Adopted AWB for")

    @admin.action(description="Download missing labels")
    def fetch_labels(self, request, queryset):
        self._run(request, queryset.exclude(awb=""), services.fetch_label, "Fetched labels for")

    @admin.action(description="Refresh tracking now")
    def refresh_tracking(self, request, queryset):
        self._run(
            request,
            queryset.filter(status__in=services.OPEN_STATUSES).exclude(awb=""),
            services.refresh_tracking,
            "Refreshed",
        )
