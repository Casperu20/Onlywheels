from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Q
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import Invoice
from .tasks import issue_invoice_task


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    actions = ("retry_failed_invoices", "mark_stale_issues_for_review")
    list_display = (
        "__str__",
        "order",
        "provider",
        "status",
        "issued_at",
        "total",
        "attempt_count",
        "efactura_status",
    )
    list_filter = ("provider", "status", "efactura_status")
    search_fields = ("number", "order__number")

    @admin.action(description="Retry pending/failed invoice or PDF requests")
    def retry_failed_invoices(self, request, queryset):
        retryable = queryset.filter(
            status__in=(Invoice.Status.PENDING, Invoice.Status.FAILED, Invoice.Status.PDF_PENDING)
        )
        order_ids = list(retryable.values_list("order_id", flat=True))
        for order_id in order_ids:
            issue_invoice_task.delay(str(order_id))

        self.message_user(
            request,
            f"Queued {len(order_ids)} invoice retry(s).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Move issue attempts older than 30 minutes to manual review")
    def mark_stale_issues_for_review(self, request, queryset):
        now = timezone.now()
        stale = queryset.filter(status=Invoice.Status.ISSUING).filter(
            Q(last_attempted_at__isnull=True) | Q(last_attempted_at__lte=now - timedelta(minutes=30))
        )
        count = stale.update(
            status=Invoice.Status.REVIEW_REQUIRED,
            last_error="Issue attempt is stale; reconcile with SmartBill before retrying.",
            updated_at=now,
        )
        self.message_user(
            request,
            f"Marked {count} stale invoice issue attempt(s) for manual reconciliation.",
            level=messages.WARNING,
        )
