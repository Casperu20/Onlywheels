from decimal import ROUND_HALF_UP, Decimal
from typing import NoReturn

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
    if voucher.max_uses is not None and voucher.used_count >= voucher.max_uses:
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


def register_use(voucher: Voucher) -> None:
    Voucher.objects.filter(pk=voucher.pk).update(used_count=F("used_count") + 1)
