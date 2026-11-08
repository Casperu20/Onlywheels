from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet

from apps.catalog.models import ProductVariant

from .models import Cart, CartItem


def purchasable_variants() -> QuerySet[ProductVariant]:
    return ProductVariant.objects.filter(is_active=True, product__is_active=True)


def get_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def cart_items(cart: Cart) -> QuerySet[CartItem]:
    return cart.items.select_related("variant__product__brand", "variant__stock").filter(
        variant__is_active=True, variant__product__is_active=True
    )


def subtotal(items: Iterable[CartItem]) -> Decimal:
    return sum((item.variant.price * item.quantity for item in items), Decimal("0.00"))


def _cap(quantity: int) -> int:
    return max(1, min(quantity, settings.CART_MAX_QUANTITY))


@transaction.atomic
def add_item(cart: Cart, variant: ProductVariant, quantity: int) -> CartItem:
    item = CartItem.objects.select_for_update().filter(cart=cart, variant=variant).first()
    if item is None:
        return CartItem.objects.create(cart=cart, variant=variant, quantity=_cap(quantity))
    item.quantity = _cap(item.quantity + quantity)
    item.save(update_fields=["quantity", "updated_at"])
    return item


def set_quantity(item: CartItem, quantity: int) -> CartItem:
    item.quantity = _cap(quantity)
    item.save(update_fields=["quantity", "updated_at"])
    return item


@transaction.atomic
def merge(cart: Cart, lines: Iterable[tuple[UUID, int]]) -> None:
    """Merge a guest (browser) cart after login in bulk. Unknown or inactive variants are skipped."""
    requested: dict[UUID, int] = {}
    for variant_id, quantity in lines:
        if quantity > 0:
            requested[variant_id] = _cap(requested.get(variant_id, 0) + quantity)
    if not requested:
        return

    from django.utils import timezone

    valid_ids = set(purchasable_variants().filter(pk__in=requested.keys()).values_list("pk", flat=True))
    if not valid_ids:
        return

    existing = {
        item.variant_id: item
        for item in CartItem.objects.select_for_update().filter(cart=cart, variant_id__in=valid_ids)
    }
    now = timezone.now()
    to_create: list[CartItem] = []
    to_update: list[CartItem] = []

    for variant_id in valid_ids:
        qty = requested[variant_id]
        if item := existing.get(variant_id):
            item.quantity = _cap(item.quantity + qty)
            item.updated_at = now
            to_update.append(item)
        else:
            to_create.append(CartItem(cart=cart, variant_id=variant_id, quantity=_cap(qty)))

    if to_create:
        CartItem.objects.bulk_create(to_create)
    if to_update:
        CartItem.objects.bulk_update(to_update, ["quantity", "updated_at"])


def clear(cart: Cart) -> None:
    cart.items.all().delete()
