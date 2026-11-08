from django.db import models

from apps.core.models import TimeStampedModel
from apps.invoicing.storage import private_invoice_storage
from apps.orders.models import Order


class Shipment(TimeStampedModel):
    class Carrier(models.TextChoices):
        SAMEDAY = "sameday", "Sameday"
        FAN_COURIER = "fan_courier", "Fan Courier"
        DEMO = "demo", "Demo courier (simulated)"

    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting AWB"
        CREATING = "creating", "Creating AWB"
        CREATED = "created", "AWB created"
        PICKED_UP = "picked_up", "Picked up"
        IN_TRANSIT = "in_transit", "In transit"
        DELIVERED = "delivered", "Delivered"
        RETURNED = "returned", "Returned"
        FAILED = "failed", "AWB failed"
        REVIEW_REQUIRED = "review_required", "Review required"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="shipment")
    carrier = models.CharField(max_length=20, choices=Carrier.choices)
    awb = models.CharField("AWB", max_length=64, blank=True)
    tracking_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # Labels hold the customer's address, so they live in the private (non-served) volume.
    label_pdf = models.FileField(storage=private_invoice_storage, upload_to="shipping/labels/", blank=True)
    parcels = models.PositiveSmallIntegerField(default=1)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    carrier_status = models.CharField(max_length=120, blank=True)
    last_error = models.TextField(blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    last_tracked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.get_carrier_display()} {self.awb or '(no AWB)'}"
