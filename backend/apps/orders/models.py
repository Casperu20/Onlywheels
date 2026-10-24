from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PAID = "paid", "Paid"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        READY_FOR_FITTING = "ready_for_fitting", "Ready for fitting"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Delivery(models.TextChoices):
        COURIER = "courier", "Courier delivery"
        GARAGE_FITTING = "garage_fitting", "Fitting at partner garage"

    number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT)
    delivery_method = models.CharField(max_length=20, choices=Delivery.choices)

    # Contact + address snapshot (billing / delivery). Kept even if the user edits their profile.
    email = models.EmailField()
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=2, default="RO")
    notes = models.TextField(blank=True)

    # Money – RON, VAT included in all amounts; `vat` is the VAT part of `total`.
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fitting = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    vat = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="RON")
    voucher = models.ForeignKey(
        "pricing.Voucher", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    voucher_code = models.CharField(max_length=32, blank=True)

    reserved_until = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "reserved_until"])]

    def __str__(self) -> str:
        return self.number


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, related_name="+")
    # Snapshot so the order stays readable if the product changes later.
    product_name = models.CharField(max_length=300)
    product_slug = models.CharField(max_length=170, blank=True)
    product_type = models.CharField(max_length=20)
    sku = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.quantity} × {self.sku}"


class OrderStatusChange(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_changes")
    status = models.CharField(max_length=30, choices=Order.Status.choices)
    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.order} → {self.status}"
