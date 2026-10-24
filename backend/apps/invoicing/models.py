from django.db import models

from apps.core.models import TimeStampedModel
from apps.orders.models import Order


class Invoice(TimeStampedModel):
    class EFacturaStatus(models.TextChoices):
        NOT_SENT = "not_sent", "Not sent"
        SENT = "sent", "Sent to ANAF"
        VALIDATED = "validated", "Validated by ANAF"
        REJECTED = "rejected", "Rejected by ANAF"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="invoice")
    series = models.CharField(max_length=10)
    number = models.CharField(max_length=20)
    issued_at = models.DateTimeField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
    pdf = models.FileField(upload_to="invoices/", blank=True)
    provider = models.CharField(max_length=20, default="smartbill")
    efactura_status = models.CharField(
        max_length=20, choices=EFacturaStatus.choices, default=EFacturaStatus.NOT_SENT
    )

    class Meta:
        ordering = ("-issued_at",)
        constraints = [
            models.UniqueConstraint(fields=["series", "number"], name="uniq_invoice_number"),
        ]

    def __str__(self) -> str:
        return f"{self.series}-{self.number}"
