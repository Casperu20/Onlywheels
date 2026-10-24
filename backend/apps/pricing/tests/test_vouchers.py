from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.pricing.models import Voucher
from apps.pricing.services import discount_for, get_valid_voucher, register_use

pytestmark = pytest.mark.django_db


def make_voucher(**fields) -> Voucher:
    defaults = {"code": "test10", "kind": Voucher.Kind.PERCENT, "value": Decimal("10")}
    return Voucher.objects.create(**{**defaults, **fields})


def test_code_is_case_insensitive():
    voucher = make_voucher()
    assert voucher.code == "TEST10"
    assert get_valid_voucher(" test10 ", Decimal("100")) == voucher


def test_percent_discount_is_rounded():
    voucher = make_voucher(value=Decimal("15"))
    assert discount_for(voucher, Decimal("99.99")) == Decimal("15.00")


def test_fixed_discount_is_capped_at_subtotal():
    voucher = make_voucher(kind=Voucher.Kind.FIXED, value=Decimal("100"))
    assert discount_for(voucher, Decimal("80.00")) == Decimal("80.00")


@pytest.mark.parametrize(
    "fields",
    [
        {"is_active": False},
        {"valid_from": timezone.now() + timedelta(days=1)},
        {"valid_until": timezone.now() - timedelta(minutes=1)},
        {"max_uses": 1, "used_count": 1},
        {"min_order_total": Decimal("500")},
    ],
)
def test_invalid_vouchers_are_rejected(fields):
    make_voucher(**fields)
    with pytest.raises(ValidationError) as exc:
        get_valid_voucher("TEST10", Decimal("100"))
    assert "voucher_code" in exc.value.detail


def test_unknown_code_is_rejected():
    with pytest.raises(ValidationError):
        get_valid_voucher("NOPE", Decimal("100"))


def test_register_use_increments():
    voucher = make_voucher(max_uses=2)
    register_use(voucher)
    voucher.refresh_from_db()
    assert voucher.used_count == 1
