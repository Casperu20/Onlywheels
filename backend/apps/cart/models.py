from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    """Server-side cart of a logged-in user. Guests keep their cart in the browser."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")

    def __str__(self) -> str:
        return f"Cart of {self.user}"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(settings.CART_MAX_QUANTITY)]
    )

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(fields=["cart", "variant"], name="uniq_cart_variant"),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} × {self.variant.sku}"
