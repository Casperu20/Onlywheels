from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel
from apps.orders.models import Order

from .storage import private_invoice_storage


class Invoice(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ISSUING = "issuing", "Issuing"
        PDF_PENDING = "pdf_pending", "PDF pending"
        ISSUED = "issued", "Issued"
        FAILED = "failed", "Failed"
        REVIEW_REQUIRED = "review_required", "Review required"

    class EFacturaStatus(models.TextChoices):
        NOT_SENT = "not_sent", "Not sent"
        SENT = "sent", "Sent to ANAF"
        VALIDATED = "validated", "Validated by ANAF"
        REJECTED = "rejected", "Rejected by ANAF"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="invoice")
    series = models.CharField(max_length=10, blank=True, default="")
    number = models.CharField(max_length=20, blank=True, default="")
    issued_at = models.DateTimeField(null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    pdf = models.FileField(storage=private_invoice_storage, upload_to="invoices/", blank=True)
    provider = models.CharField(max_length=20, default="smartbill")
    provider_reference = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    last_error = models.TextField(blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    efactura_status = models.CharField(max_length=20, choices=EFacturaStatus.choices, default=EFacturaStatus.NOT_SENT)

    class Meta:
        ordering = ("-issued_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["series", "number"],
                condition=~Q(series="") & ~Q(number=""),
                name="uniq_invoice_number",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.series}-{self.number}"
