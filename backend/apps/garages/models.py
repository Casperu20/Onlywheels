from datetime import time

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


def default_working_days() -> list[int]:
    return [0, 1, 2, 3, 4, 5]  # Monday–Saturday


class Garage(TimeStampedModel):
    """Partner service that mounts the wheels. Staff in `partner_users` see its appointments."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    opens_at = models.TimeField(default=time(8, 0))
    closes_at = models.TimeField(default=time(18, 0))
    working_days = models.JSONField(
        default=default_working_days, help_text="Weekdays, 0 = Monday … 6 = Sunday"
    )
    slot_minutes = models.PositiveSmallIntegerField(default=60)
    capacity_per_slot = models.PositiveSmallIntegerField(
        default=2, help_text="How many cars can be fitted in parallel"
    )
    fitting_price = models.DecimalField(
        max_digits=8, decimal_places=2, default=150, help_text="RON for mounting + balancing a set"
    )
    is_active = models.BooleanField(default=True)
    partner_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="partner_garages"
    )

    class Meta:
        ordering = ("city", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.city})"
