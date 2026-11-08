from decimal import Decimal

import pytest

from apps.orders import services as order_services
from apps.orders.models import Order, OrderItem
from apps.shipping import services
from apps.shipping.models import Shipment
from apps.shipping.providers import CarrierConfigurationError, get_carrier_provider
from tests.factories import make_order

pytestmark = pytest.mark.django_db

Status = Shipment.Status


@pytest.fixture
def demo(settings, tmp_path):
    settings.SHIPPING_CARRIER = "demo"
    settings.PRIVATE_INVOICE_ROOT = tmp_path


def shipped_order(user, capture):
    order = make_order(user, status=Order.Status.PAID)
    OrderItem.objects.create(
        order=order,
        product_name="Wheel",
        product_type="wheel",
        sku="W1",
        unit_price=Decimal("100"),
        quantity=2,
        line_total=Decimal("200"),
        shipping_weight_kg=Decimal("11.00"),
    )
    with capture(execute=True):
        order_services.change_status(order, Order.Status.PROCESSING)
    order.refresh_from_db()
    return order


def test_demo_carrier_creates_a_marked_awb_and_a_pdf_label(user, demo, django_capture_on_commit_callbacks):
    order = shipped_order(user, django_capture_on_commit_callbacks)

    shipment = order.shipment
    assert order.status == Order.Status.SHIPPED
    assert shipment.carrier == "demo"
    assert shipment.get_carrier_display() == "Demo courier (simulated)"
    assert shipment.awb.startswith("DEMO")
    assert shipment.tracking_url == ""
    assert shipment.status == Status.CREATED
    with shipment.label_pdf.open("rb") as label:
        pdf = label.read()
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    assert shipment.awb.encode() in pdf
    assert b"SIMULATED" in pdf


def test_each_tracking_refresh_moves_one_step_until_delivered(user, demo, django_capture_on_commit_callbacks):
    shipment = shipped_order(user, django_capture_on_commit_callbacks).shipment

    seen = []
    for _ in range(4):
        services.refresh_tracking(shipment)
        shipment.refresh_from_db()
        seen.append(shipment.status)

    assert seen == [Status.PICKED_UP, Status.IN_TRANSIT, Status.DELIVERED, Status.DELIVERED]
    assert shipment.carrier_status
    assert shipment.order.status == Order.Status.COMPLETED


def test_demo_label_is_regenerated_from_the_awb_alone(demo):
    pdf = get_carrier_provider("demo").download_label("DEMO123")

    assert pdf.startswith(b"%PDF") and b"DEMO123" in pdf


def test_unknown_carrier_message_lists_demo(settings):
    settings.SHIPPING_CARRIER = "dhl"

    with pytest.raises(CarrierConfigurationError, match="demo"):
        get_carrier_provider()
