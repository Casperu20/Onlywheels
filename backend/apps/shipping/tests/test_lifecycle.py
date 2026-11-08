from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from rest_framework.test import APIClient

from apps.orders import services as order_services
from apps.orders.models import Order, OrderItem
from apps.shipping import services
from apps.shipping.models import Shipment
from apps.shipping.providers import (
    AwbResult,
    CarrierAmbiguousError,
    CarrierRejectedError,
    TrackingUpdate,
)
from apps.shipping.tasks import refresh_shipments_task
from tests.factories import make_order

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 label"
Status = Shipment.Status


@pytest.fixture
def carrier(settings, tmp_path):
    settings.SHIPPING_CARRIER = "sameday"
    settings.PRIVATE_INVOICE_ROOT = tmp_path
    provider = Mock()
    provider.name = "sameday"
    provider.display_name = "Sameday"
    provider.create_awb.return_value = AwbResult(awb="1ONB1", tracking_url="https://track.example/1ONB1")
    provider.download_label.return_value = PDF
    provider.track.return_value = TrackingUpdate(status=None, label="")
    with patch("apps.shipping.services.get_carrier_provider", return_value=provider):
        yield provider


def paid_order(user, **fields):
    order = make_order(user, **{"status": Order.Status.PAID, **fields})
    OrderItem.objects.create(
        order=order,
        product_name="Wheel",
        product_type="wheel",
        sku="W1",
        unit_price=Decimal("100"),
        quantity=4,
        line_total=Decimal("400"),
        shipping_weight_kg=Decimal("11.00"),
    )
    return order


def to_processing(order, capture):
    with capture(execute=True):
        order_services.change_status(order, Order.Status.PROCESSING)
    order.refresh_from_db()
    return order


# --- AWB creation -------------------------------------------------------------------------


def test_processing_courier_order_creates_awb_and_ships(user, carrier, django_capture_on_commit_callbacks):
    order = to_processing(paid_order(user), django_capture_on_commit_callbacks)

    shipment = order.shipment
    assert order.status == Order.Status.SHIPPED
    assert (shipment.status, shipment.awb, shipment.carrier) == (Status.CREATED, "1ONB1", "sameday")
    assert shipment.tracking_url == "https://track.example/1ONB1"
    assert shipment.parcels == 4
    assert shipment.weight_kg == Decimal("44.00")
    assert shipment.attempt_count == 1
    with shipment.label_pdf.open("rb") as label:
        assert label.read() == PDF
    with pytest.raises(ValueError):
        str(shipment.label_pdf.url)
    carrier.create_awb.assert_called_once()
    assert carrier.create_awb.call_args.kwargs["parcels"] == [Decimal("11.00")] * 4
    assert order.status_changes.filter(status=Order.Status.SHIPPED, note__contains="1ONB1").exists()


def test_garage_fitting_orders_never_get_an_awb(user, carrier, django_capture_on_commit_callbacks):
    order = to_processing(
        paid_order(user, delivery_method=Order.Delivery.GARAGE_FITTING), django_capture_on_commit_callbacks
    )
    assert order.status == Order.Status.PROCESSING
    assert not Shipment.objects.filter(order=order).exists()
    carrier.create_awb.assert_not_called()


def test_disabled_carrier_leaves_the_manual_flow_untouched(user, settings, django_capture_on_commit_callbacks):
    settings.SHIPPING_CARRIER = ""
    order = to_processing(paid_order(user), django_capture_on_commit_callbacks)
    assert order.status == Order.Status.PROCESSING
    assert not Shipment.objects.filter(order=order).exists()


def test_rejected_awb_keeps_the_order_processing(user, carrier, django_capture_on_commit_callbacks):
    carrier.create_awb.side_effect = CarrierRejectedError("City not found")
    order = to_processing(paid_order(user), django_capture_on_commit_callbacks)

    assert order.status == Order.Status.PROCESSING
    assert order.shipment.status == Status.FAILED
    assert order.shipment.last_error == "City not found"
    assert order.shipment.awb == ""


def test_failed_shipment_can_be_retried(user, carrier, django_capture_on_commit_callbacks):
    carrier.create_awb.side_effect = [CarrierRejectedError("down"), AwbResult(awb="1ONB2", tracking_url="")]
    order = to_processing(paid_order(user), django_capture_on_commit_callbacks)

    with django_capture_on_commit_callbacks(execute=True):
        services.retry_shipment(order.shipment)

    order.refresh_from_db()
    assert order.status == Order.Status.SHIPPED
    assert order.shipment.awb == "1ONB2"
    assert order.shipment.attempt_count == 2
    assert order.shipment.last_error == ""


def test_ambiguous_outcome_requires_review_and_is_not_auto_retried(user, carrier, django_capture_on_commit_callbacks):
    carrier.create_awb.side_effect = CarrierAmbiguousError("search reference in portal")
    order = to_processing(paid_order(user), django_capture_on_commit_callbacks)
    assert order.shipment.status == Status.REVIEW_REQUIRED

    services.create_shipment(order)
    with pytest.raises(services.ShipmentStateError):
        services.retry_shipment(order.shipment)
    assert carrier.create_awb.call_count == 1

    services.retry_shipment(order.shipment, confirmed_absent=True)
    assert carrier.create_awb.call_count == 2


def test_missing_weight_fails_without_calling_the_carrier(user, carrier, django_capture_on_commit_callbacks):
    order = paid_order(user)
    order.items.update(shipping_weight_kg=None)
    order = to_processing(order, django_capture_on_commit_callbacks)

    assert order.shipment.status == Status.FAILED
    assert "W1" in order.shipment.last_error
    carrier.create_awb.assert_not_called()


def test_create_shipment_is_idempotent(user, carrier, django_capture_on_commit_callbacks):
    order = to_processing(paid_order(user), django_capture_on_commit_callbacks)
    services.create_shipment(order)
    assert carrier.create_awb.call_count == 1
    assert Shipment.objects.filter(order=order).count() == 1


def test_label_failure_keeps_the_awb_and_can_be_fetched_later(user, carrier, django_capture_on_commit_callbacks):
    carrier.download_label.side_effect = [CarrierRejectedError("no pdf"), PDF]
    order = to_processing(paid_order(user), django_capture_on_commit_callbacks)

    shipment = order.shipment
    assert order.status == Order.Status.SHIPPED
    assert (shipment.status, shipment.awb, shipment.label_pdf.name) == (Status.CREATED, "1ONB1", "")
    assert "label" in shipment.last_error.lower()

    services.fetch_label(shipment)
    shipment.refresh_from_db()
    assert shipment.label_pdf.name
    assert shipment.last_error == ""
    assert carrier.create_awb.call_count == 1


# --- Tracking -----------------------------------------------------------------------------


def shipped(user, status=Status.CREATED):
    order = make_order(user, status=Order.Status.SHIPPED)
    return Shipment.objects.create(order=order, carrier="sameday", awb="1ONB9", status=status)


def test_tracking_moves_forward(user, carrier):
    shipment = shipped(user)
    carrier.track.return_value = TrackingUpdate(status=Status.IN_TRANSIT, label="In tranzit")
    services.refresh_tracking(shipment)
    shipment.refresh_from_db()
    assert shipment.status == Status.IN_TRANSIT
    assert shipment.carrier_status == "In tranzit"
    assert shipment.last_tracked_at is not None


def test_tracking_never_regresses(user, carrier):
    shipment = shipped(user, status=Status.IN_TRANSIT)
    carrier.track.return_value = TrackingUpdate(status=Status.PICKED_UP, label="Ridicat")
    services.refresh_tracking(shipment)
    shipment.refresh_from_db()
    assert shipment.status == Status.IN_TRANSIT


def test_unknown_carrier_status_is_recorded_but_not_applied(user, carrier):
    shipment = shipped(user)
    carrier.track.return_value = TrackingUpdate(status=None, label="Status nou")
    services.refresh_tracking(shipment)
    shipment.refresh_from_db()
    assert (shipment.status, shipment.carrier_status) == (Status.CREATED, "Status nou")


def test_delivery_completes_the_courier_order(user, carrier, django_capture_on_commit_callbacks):
    shipment = shipped(user, status=Status.IN_TRANSIT)
    carrier.track.return_value = TrackingUpdate(status=Status.DELIVERED, label="Livrat")
    with django_capture_on_commit_callbacks(execute=True):
        services.refresh_tracking(shipment)
    shipment.order.refresh_from_db()
    assert shipment.order.status == Order.Status.COMPLETED


def test_tracking_errors_are_recorded_not_raised(user, carrier):
    shipment = shipped(user)
    carrier.track.side_effect = CarrierRejectedError("tracking down")
    services.refresh_tracking(shipment)
    shipment.refresh_from_db()
    assert shipment.status == Status.CREATED
    assert shipment.last_error == "tracking down"


def test_periodic_task_polls_only_open_shipments(user, carrier):
    open_one = shipped(user, status=Status.IN_TRANSIT)
    shipped(user, status=Status.DELIVERED)
    shipped(user, status=Status.RETURNED)
    Shipment.objects.create(order=make_order(user), carrier="sameday", status=Status.FAILED)

    assert refresh_shipments_task() == 1
    carrier.track.assert_called_once_with(open_one.awb)


# --- Admin --------------------------------------------------------------------------------


@pytest.fixture
def admin_client(db):
    from django.test import Client

    from apps.accounts.models import User

    client = Client()
    client.force_login(User.objects.create_superuser(email="admin@example.test", password="Adm1n-Passw0rd!"))
    return client


def _admin_action(client, action, shipment):
    from django.urls import reverse

    return client.post(
        reverse("admin:shipping_shipment_changelist"),
        {"action": action, "_selected_action": [str(shipment.pk)]},
        follow=True,
    )


def test_admin_retries_failed_shipments_only(user, carrier, admin_client):
    order = paid_order(user, status=Order.Status.PROCESSING)
    failed = Shipment.objects.create(order=order, carrier="sameday", status=Status.FAILED, last_error="down")
    review = Shipment.objects.create(
        order=paid_order(user, status=Order.Status.PROCESSING), carrier="sameday", status=Status.REVIEW_REQUIRED
    )

    assert _admin_action(admin_client, "retry_failed", failed).status_code == 200
    assert _admin_action(admin_client, "retry_failed", review).status_code == 200

    failed.refresh_from_db()
    review.refresh_from_db()
    assert (failed.status, failed.awb) == (Status.CREATED, "1ONB1")
    assert review.status == Status.REVIEW_REQUIRED
    assert carrier.create_awb.call_count == 1


def test_admin_retry_after_review_confirmation(user, carrier, admin_client):
    shipment = Shipment.objects.create(
        order=paid_order(user, status=Order.Status.PROCESSING), carrier="sameday", status=Status.REVIEW_REQUIRED
    )
    _admin_action(admin_client, "retry_confirmed_absent", shipment)
    shipment.refresh_from_db()
    assert shipment.status == Status.CREATED


def test_admin_adopts_a_manually_entered_awb(user, carrier, admin_client, django_capture_on_commit_callbacks):
    shipment = Shipment.objects.create(
        order=paid_order(user, status=Order.Status.PROCESSING),
        carrier="sameday",
        status=Status.REVIEW_REQUIRED,
        awb="1ONBMANUAL",
    )
    with django_capture_on_commit_callbacks(execute=True):
        _admin_action(admin_client, "adopt_manual_awb", shipment)

    shipment.refresh_from_db()
    shipment.order.refresh_from_db()
    assert shipment.status == Status.CREATED
    assert shipment.tracking_url == "https://sameday.ro/#awb=1ONBMANUAL"
    assert shipment.order.status == Order.Status.SHIPPED
    carrier.create_awb.assert_not_called()


def test_adopting_requires_an_awb(user, carrier):
    shipment = Shipment.objects.create(
        order=paid_order(user, status=Order.Status.PROCESSING), carrier="sameday", status=Status.REVIEW_REQUIRED
    )
    with pytest.raises(services.ShipmentStateError):
        services.adopt_manual_awb(shipment)


def test_staff_can_download_private_label(user, carrier, admin_client, django_capture_on_commit_callbacks):
    from django.test import Client
    from django.urls import reverse

    order = to_processing(paid_order(user), django_capture_on_commit_callbacks)
    url = reverse("admin:shipping_shipment_label", args=[order.shipment.pk])

    response = admin_client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert b"".join(response.streaming_content) == PDF

    customer = Client()
    customer.force_login(user)
    assert customer.get(url).status_code == 302


# --- Customer API -------------------------------------------------------------------------


def test_owner_sees_tracking_but_not_internal_errors(user, carrier):
    shipment = shipped(user, status=Status.IN_TRANSIT)
    shipment.tracking_url = "https://track.example/1ONB9"
    shipment.last_error = "internal"
    shipment.save()
    client = APIClient()
    client.force_authenticate(user)

    body = client.get(f"/api/v1/orders/{shipment.order.number}/").json()

    assert body["shipment"] == {
        "carrier": "sameday",
        "carrier_display": "Sameday",
        "awb": "1ONB9",
        "tracking_url": "https://track.example/1ONB9",
        "status": "in_transit",
    }


def test_shipment_without_awb_is_hidden_from_customer(user, carrier):
    order = make_order(user, status=Order.Status.PROCESSING)
    Shipment.objects.create(order=order, carrier="sameday", status=Status.FAILED, last_error="x")
    client = APIClient()
    client.force_authenticate(user)
    assert client.get(f"/api/v1/orders/{order.number}/").json()["shipment"] is None
