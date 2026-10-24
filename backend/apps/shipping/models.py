from django.db import models

from apps.core.models import TimeStampedModel
from apps.orders.models import Order


class Shipment(TimeStampedModel):
    class Carrier(models.TextChoices):
        SAMEDAY = "sameday", "Sameday"
        FAN_COURIER = "fan_courier", "Fan Courier"

    class Status(models.TextChoices):
        CREATED = "created", "AWB created"
        PICKED_UP = "picked_up", "Picked up"
        IN_TRANSIT = "in_transit", "In transit"
        DELIVERED = "delivered", "Delivered"
        RETURNED = "returned", "Returned"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="shipment")
    carrier = models.CharField(max_length=20, choices=Carrier.choices)
    awb = models.CharField("AWB", max_length=64, blank=True)
    tracking_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    label_pdf = models.FileField(upload_to="shipping/labels/", blank=True)
    parcels = models.PositiveSmallIntegerField(default=1)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.get_carrier_display()} {self.awb or '(no AWB)'}"
