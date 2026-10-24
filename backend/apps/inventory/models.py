from django.db import models
from simple_history.models import HistoricalRecords

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel


class StockItem(TimeStampedModel):
    """Stock for one variant. `reserved` is held by unpaid orders (phase E)."""

    variant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE, related_name="stock")
    quantity = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)

    history = HistoricalRecords()

    class Meta:
        ordering = ("variant__sku",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(reserved__lte=models.F("quantity")),
                name="stock_reserved_lte_quantity",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.variant.sku}: {self.available} available"

    @property
    def available(self) -> int:
        return max(self.quantity - self.reserved, 0)


def in_stock_q(prefix: str = "") -> models.Q:
    """Filter for variants (or related rows via `prefix`) that have available stock."""
    return models.Q(**{f"{prefix}stock__quantity__gt": models.F(f"{prefix}stock__reserved")})


def available_for(variant: ProductVariant) -> int:
    try:
        return variant.stock.available
    except StockItem.DoesNotExist:
        return 0
