from decimal import Decimal

import pytest

from apps.catalog.models import ProductType, ProductVariant
from apps.fitment import services
from tests.factories import make_generation, make_product, make_tire, make_variant

pytestmark = pytest.mark.django_db


@pytest.fixture
def spec():
    # 5x112, hub 66.6, ET 20-40, 17-20", 7.5-9.0J, M14x1.25, tires 225/45 R18 + 225/40 R19
    return make_generation().fitment


@pytest.fixture
def wheel_product():
    return make_product(type=ProductType.WHEEL)


def test_wheel_with_exact_bore_fits_without_rings(spec, wheel_product):
    result = services.check_variant(spec, make_variant(wheel_product))
    assert result == services.FitmentResult(fits=True)


def test_wheel_with_larger_bore_fits_with_hub_rings(spec, wheel_product):
    result = services.check_variant(spec, make_variant(wheel_product, center_bore_mm=Decimal("72.6")))
    assert result.fits
    assert result.needs_hub_rings


@pytest.mark.parametrize(
    ("fields", "issue"),
    [
        ({"pcd": "5x120"}, services.PCD_MISMATCH),
        ({"center_bore_mm": Decimal("57.1")}, services.CENTER_BORE_TOO_SMALL),
        ({"et_mm": 45}, services.OFFSET_OUT_OF_RANGE),
        ({"et_mm": 19}, services.OFFSET_OUT_OF_RANGE),
        ({"diameter_in": 16}, services.DIAMETER_OUT_OF_RANGE),
        ({"diameter_in": 21}, services.DIAMETER_OUT_OF_RANGE),
        ({"width_in": Decimal("9.5")}, services.WIDTH_OUT_OF_RANGE),
    ],
)
def test_wheel_rejections(spec, wheel_product, fields, issue):
    result = services.check_variant(spec, make_variant(wheel_product, **fields))
    assert not result.fits
    assert not result.needs_hub_rings
    assert issue in result.issues


def test_range_limits_are_inclusive(spec, wheel_product):
    variant = make_variant(wheel_product, et_mm=40, diameter_in=20, width_in=Decimal("9.0"))
    assert services.check_variant(spec, variant).fits


def test_tire_must_be_oem_size(spec):
    product = make_product(type=ProductType.TIRE, brand="Continental")
    assert services.check_variant(spec, make_tire(product, (225, 45, 18))).fits
    result = services.check_variant(spec, make_tire(product, (205, 55, 16)))
    assert result.issues == (services.TIRE_SIZE_NOT_OEM,)


def test_set_checks_wheel_and_tire(spec):
    product = make_product(type=ProductType.SET, brand="OnlyWheels")
    good = make_variant(product, diameter_in=18, tire_width_mm=225, tire_aspect=45)
    bad_tire = make_variant(product, diameter_in=18, tire_width_mm=245, tire_aspect=40)
    assert services.check_variant(spec, good).fits
    assert services.check_variant(spec, bad_tire).issues == (services.TIRE_SIZE_NOT_OEM,)


def test_accessory_thread(spec):
    product = make_product(type=ProductType.ACCESSORY, brand="OnlyWheels")
    assert services.check_variant(spec, make_variant(product, thread_size="M14x1.25")).fits
    assert services.check_variant(spec, make_variant(product)).fits
    wrong = services.check_variant(spec, make_variant(product, thread_size="M14x1.5"))
    assert wrong.issues == (services.THREAD_MISMATCH,)


def test_database_filter_agrees_with_python_check(spec):
    wheel = make_product(type=ProductType.WHEEL)
    tire = make_product(type=ProductType.TIRE, brand="Michelin")
    wheel_set = make_product(type=ProductType.SET, brand="OnlyWheels")
    accessory = make_product(type=ProductType.ACCESSORY, brand="OnlyWheels")

    for fields in [
        {},
        {"center_bore_mm": Decimal("72.6")},
        {"center_bore_mm": Decimal("57.1")},
        {"pcd": "5x120"},
        {"et_mm": 20},
        {"et_mm": 41},
        {"diameter_in": 17},
        {"diameter_in": 21},
        {"width_in": Decimal("7.5")},
        {"width_in": Decimal("7.0")},
    ]:
        make_variant(wheel, **fields)
    for size in [(225, 45, 18), (225, 40, 19), (205, 55, 16)]:
        make_tire(tire, size)
    make_variant(wheel_set, tire_width_mm=225, tire_aspect=45)
    make_variant(wheel_set, tire_width_mm=245, tire_aspect=40)
    make_variant(wheel_set)
    make_variant(accessory, thread_size="M14x1.25")
    make_variant(accessory, thread_size="M14x1.5")
    make_variant(accessory)

    variants = ProductVariant.objects.select_related("product")
    expected = {v.pk for v in variants if services.check_variant(spec, v).fits}
    actual = set(variants.filter(services.compatible_variants_q(spec)).values_list("pk", flat=True))

    assert actual == expected
    assert len(expected) == 11  # 5 wheels + 2 tires + 2 sets + 2 accessories
