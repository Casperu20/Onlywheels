from decimal import ROUND_HALF_UP, Decimal
from typing import NoReturn

from django.db import models
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Voucher

CENT = Decimal("0.01")


def _reject(message: str) -> NoReturn:
    raise ValidationError({"voucher_code": [message]})


def get_valid_voucher(code: str, subtotal: Decimal) -> Voucher:
    """Return the voucher or raise a validation error on the `voucher_code` field."""
    voucher = Voucher.objects.filter(code=code.strip().upper(), is_active=True).first()
    now = timezone.now()
    if voucher is None or voucher.valid_from > now:
        _reject("This voucher code is not valid.")
    if voucher.valid_until and voucher.valid_until < now:
        _reject("This voucher has expired.")
    if voucher.max_uses is not None and (voucher.used_count + voucher.reserved_count >= voucher.max_uses):
        _reject("This voucher has already been used up.")
    if subtotal < voucher.min_order_total:
        _reject(f"This voucher requires a minimum order of {voucher.min_order_total} RON.")
    return voucher


def discount_for(voucher: Voucher, subtotal: Decimal) -> Decimal:
    if voucher.kind == Voucher.Kind.PERCENT:
        amount = (subtotal * voucher.value / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        amount = voucher.value
    return min(amount, subtotal)


def reserve_voucher(voucher: Voucher) -> None:
    """Atomically reserve a voucher slot for an unpaid order."""
    locked = Voucher.objects.select_for_update().filter(pk=voucher.pk).first()
    if locked is None or not locked.is_active:
        _reject("This voucher code is not valid.")
    now = timezone.now()
    if locked.valid_until and locked.valid_until < now:
        _reject("This voucher has expired.")
    if locked.max_uses is not None and (locked.used_count + locked.reserved_count >= locked.max_uses):
        _reject("This voucher has already been used up.")
    Voucher.objects.filter(pk=locked.pk).update(reserved_count=F("reserved_count") + 1)


def release_voucher(voucher: Voucher) -> None:
    """Release a reserved voucher slot when an order is cancelled or expired."""
    Voucher.objects.filter(pk=voucher.pk, reserved_count__gt=0).update(
        reserved_count=F("reserved_count") - 1
    )


def release_used_voucher(voucher: Voucher | str) -> None:
    """Decrement used_count when a confirmed/paid order is cancelled or returned."""
    pk = voucher.pk if isinstance(voucher, Voucher) else voucher
    Voucher.objects.filter(pk=pk, used_count__gt=0).update(used_count=F("used_count") - 1)


def register_use(voucher: Voucher, was_reserved: bool = True) -> None:
    """Commit voucher usage on order payment."""
    if was_reserved:
        Voucher.objects.filter(pk=voucher.pk).update(
            used_count=F("used_count") + 1,
            reserved_count=models.Case(
                models.When(reserved_count__gt=0, then=F("reserved_count") - 1),
                default=models.Value(0),
            ),
        )
    else:
        Voucher.objects.filter(pk=voucher.pk).update(used_count=F("used_count") + 1)
