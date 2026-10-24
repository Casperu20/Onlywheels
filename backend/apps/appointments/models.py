from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.garages.models import Garage


class Appointment(TimeStampedModel):
    class Status(models.TextChoices):
        HELD = "held", "Held (waiting for payment)"
        BOOKED = "booked", "Booked (paid)"
        CONFIRMED = "confirmed", "Confirmed by garage"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    ACTIVE_STATUSES = (Status.HELD, Status.BOOKED, Status.CONFIRMED)

    garage = models.ForeignKey(Garage, on_delete=models.PROTECT, related_name="appointments")
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="appointment")
    slot_start = models.DateTimeField()
    slot_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.HELD)
    garage_note = models.TextField(blank=True)

    class Meta:
        ordering = ("slot_start",)
        indexes = [models.Index(fields=["garage", "slot_start"])]

    def __str__(self) -> str:
        return f"{self.garage} – {timezone.localtime(self.slot_start):%Y-%m-%d %H:%M}"
