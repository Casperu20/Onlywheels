from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.catalog.management.commands.seed_catalog import PRODUCTS, default_weight_kg
from apps.catalog.models import ProductType
from apps.orders import services as order_services
from apps.orders.models import OrderItem
from apps.shipping.models import Shipment
from apps.shipping.services import ShipmentDataError, parcel_weights
from tests.factories import add_to_cart, checkout_payload, make_order, make_product, make_variant

pytestmark = pytest.mark.django_db


def add_item(order, *, sku="W", product_type=ProductType.WHEEL, quantity=1, weight="11.00"):
    return OrderItem.objects.create(
        order=order,
        product_name=sku,
        product_type=product_type,
        sku=sku,
        unit_price=Decimal("100"),
        quantity=quantity,
        line_total=Decimal("100") * quantity,
        shipping_weight_kg=Decimal(weight) if weight is not None else None,
    )


# --- Weights and shipment state ---------------------------------------------------------


@pytest.mark.parametrize("weight", ["0", "-1.5"])
def test_variant_weight_must_be_positive(weight):
    variant = make_variant(make_product())
    variant.shipping_weight_kg = Decimal(weight)
    with pytest.raises(ValidationError) as exc:
        variant.full_clean()
    assert "shipping_weight_kg" in exc.value.message_dict


@pytest.mark.parametrize("product_type", [ProductType.WHEEL, ProductType.TIRE, ProductType.SET, ProductType.ACCESSORY])
def test_factory_variants_have_a_positive_weight(product_type):
    product = make_product(type=product_type)
    if product_type == ProductType.TIRE:
        variant = make_variant(product, tire_width_mm=225, tire_aspect=45, diameter_in=18)
    else:
        variant = make_variant(product)
    assert variant.shipping_weight_kg > 0


def test_every_seeded_variant_gets_a_demo_weight():
    for product in PRODUCTS:
        for variant in product["variants"]:
            assert default_weight_kg(product["type"], variant) > 0


def test_order_items_snapshot_the_variant_weight(user):
    variant = make_variant(make_product(), price="200", shipping_weight_kg=Decimal("11.50"))
    add_to_cart(user, variant, 4)
    order = order_services.place_order(user, checkout_payload())

    variant.shipping_weight_kg = Decimal("20.00")
    variant.save()

    item = OrderItem.objects.get(order=order)
    assert item.shipping_weight_kg == Decimal("11.50")


def test_parcel_weights_give_one_parcel_per_unit_and_bundle_accessories(user):
    order = make_order(user)
    add_item(order, sku="W", quantity=2, weight="11.00")
    add_item(order, sku="A", product_type=ProductType.ACCESSORY, quantity=3, weight="0.50")
    assert parcel_weights(order) == [Decimal("11.00"), Decimal("11.00"), Decimal("1.50")]


def test_parcel_weights_reject_an_item_without_weight(user):
    order = make_order(user)
    add_item(order, sku="W-NOWEIGHT", weight=None)
    with pytest.raises(ShipmentDataError, match="W-NOWEIGHT"):
        parcel_weights(order)


def test_new_shipment_is_pending_without_awb(user):
    shipment = Shipment.objects.create(order=make_order(user), carrier=Shipment.Carrier.SAMEDAY)
    assert shipment.status == Shipment.Status.PENDING
    assert shipment.awb == ""
    assert shipment.last_error == ""
    assert shipment.attempt_count == 0
