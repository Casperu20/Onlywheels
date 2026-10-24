from django.db import models

from apps.core.models import TimeStampedModel
from apps.orders.models import Order


class Payment(TimeStampedModel):
    """One online payment attempt (a Stripe Checkout session). An order may have several."""

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=20)
    session_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="RON")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    payment_reference = models.CharField(max_length=255, blank=True, help_text="e.g. Stripe PaymentIntent id")
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.provider} {self.session_id} ({self.status})"


class WebhookEvent(TimeStampedModel):
    """Processed provider events, so retried webhooks are handled only once."""

    provider = models.CharField(max_length=20)
    event_id = models.CharField(max_length=255)
    type = models.CharField(max_length=100)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=["provider", "event_id"], name="uniq_webhook_event"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.type}:{self.event_id}"
