from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.cart.models import CartItem
from apps.inventory.models import StockItem
from apps.invoicing.models import Invoice
from apps.orders import services
from apps.orders.models import Order
from apps.pricing.models import Voucher
from tests.factories import (
    add_to_cart,
    checkout_payload,
    future_slot,
    make_garage,
    make_order,
    make_product,
    make_variant,
)

pytestmark = pytest.mark.django_db

PREVIEW = "/api/v1/checkout/preview/"
ORDERS = "/api/v1/orders/"


@pytest.fixture
def variant():
    return make_variant(make_product(), price="200", stock=10)


@pytest.fixture
def cart(user, variant):
    add_to_cart(user, variant, 4)  # 800 RON


def stock_of(variant) -> StockItem:
    return StockItem.objects.get(variant=variant)


# --- Quote ------------------------------------------------------------------


def test_preview_courier_below_free_shipping(auth_client, cart):
    data = auth_client.post(PREVIEW, {"delivery_method": "courier"}, format="json").json()
    assert data == {
        "subtotal": "800.00",
        "discount": "0.00",
        "shipping": "25.00",
        "fitting": "0.00",
        "total": "825.00",
        "vat": "143.18",
        "voucher_code": None,
    }


def test_preview_free_shipping_above_threshold(auth_client, user, variant, cart):
    add_to_cart(user, variant, 1)  # 1000 RON
    data = auth_client.post(PREVIEW, {"delivery_method": "courier"}, format="json").json()
    assert data["shipping"] == "0.00"
    assert data["total"] == "1000.00"


def test_preview_garage_fitting(auth_client, cart):
    garage = make_garage(fitting_price=Decimal("150"))
    data = auth_client.post(
        PREVIEW, {"delivery_method": "garage_fitting", "garage_id": str(garage.pk)}, format="json"
    ).json()
    assert (data["shipping"], data["fitting"], data["total"]) == ("0.00", "150.00", "950.00")


def test_preview_garage_fitting_requires_garage(auth_client, cart):
    response = auth_client.post(PREVIEW, {"delivery_method": "garage_fitting"}, format="json")
    assert "garage_id" in response.json()["error"]["fields"]


def test_preview_with_voucher(auth_client, cart):
    Voucher.objects.create(code="TEN", value=Decimal("10"), min_order_total=Decimal("500"))
    data = auth_client.post(
        PREVIEW, {"delivery_method": "courier", "voucher_code": "ten"}, format="json"
    ).json()
    assert (data["discount"], data["shipping"], data["total"]) == ("80.00", "25.00", "745.00")
    assert data["voucher_code"] == "TEN"


def test_preview_with_invalid_voucher(auth_client, cart):
    response = auth_client.post(PREVIEW, {"delivery_method": "courier", "voucher_code": "NOPE"}, format="json")
    assert response.status_code == 400
    assert "voucher_code" in response.json()["error"]["fields"]


def test_preview_empty_cart(auth_client):
    response = auth_client.post(PREVIEW, {"delivery_method": "courier"}, format="json")
    assert response.status_code == 400


# --- Placing orders -----------------------------------------------------------


def test_place_courier_order_reserves_stock_and_empties_cart(auth_client, user, variant, cart):
    response = auth_client.post(ORDERS, checkout_payload(), format="json")

    assert response.status_code == 201, response.content
    data = response.json()
    assert data["status"] == "pending_payment"
    assert data["total"] == "825.00"
    assert data["can_pay"] is True
    assert data["items"][0]["quantity"] == 4
    assert data["items"][0]["description"].startswith('18"')
    assert stock_of(variant).reserved == 4
    assert CartItem.objects.filter(cart__user=user).count() == 0
    assert data["status_changes"][0]["status"] == "pending_payment"


def test_checkout_validation(auth_client, cart):
    response = auth_client.post(
        ORDERS, checkout_payload(accept_terms=False, postal_code="12", phone="abc"), format="json"
    )
    fields = response.json()["error"]["fields"]
    assert {"accept_terms", "postal_code", "phone"} <= set(fields)


def test_out_of_stock_returns_409_and_keeps_cart(auth_client, user, variant, cart):
    StockItem.objects.filter(variant=variant).update(quantity=2)

    response = auth_client.post(ORDERS, checkout_payload(), format="json")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "out_of_stock"
    assert variant.sku in response.json()["error"]["message"]
    assert Order.objects.count() == 0
    assert CartItem.objects.filter(cart__user=user).count() == 1


def test_garage_fitting_order_holds_slot(auth_client, cart):
    garage = make_garage(capacity_per_slot=1)
    slot = future_slot(garage)
    payload = checkout_payload(
        delivery_method="garage_fitting", garage_id=str(garage.pk), slot_start=slot.isoformat()
    )

    data = auth_client.post(ORDERS, payload, format="json").json()

    assert data["fitting"] == "150.00"
    assert data["appointment"]["status"] == "held"
    assert data["appointment"]["garage"]["slug"] == garage.slug


def test_taken_slot_is_rejected(auth_client, user, variant, cart):
    garage = make_garage(capacity_per_slot=1)
    slot = future_slot(garage)
    payload = checkout_payload(
        delivery_method="garage_fitting", garage_id=str(garage.pk), slot_start=slot.isoformat()
    )
    assert auth_client.post(ORDERS, payload, format="json").status_code == 201

    add_to_cart(user, variant, 1)
    response = auth_client.post(ORDERS, payload, format="json")
    assert response.status_code == 400
    assert "slot_start" in response.json()["error"]["fields"]
    assert stock_of(variant).reserved == 4  # second attempt rolled back


def test_orders_are_private(auth_client):
    other = User.objects.create_user(email="other@example.com", password="x")
    order = make_order(other)
    assert auth_client.get(f"{ORDERS}{order.number}/").status_code == 404
    assert auth_client.get(ORDERS).json()["results"] == []


# --- Lifecycle ----------------------------------------------------------------


def place(user) -> Order:
    return services.place_order(user, {**checkout_payload(), "delivery_method": "courier"})


def test_expired_orders_release_stock(user, variant, cart):
    order = place(user)
    Order.objects.filter(pk=order.pk).update(reserved_until=timezone.now() - timedelta(minutes=1))

    assert services.expire_unpaid_orders() == 1

    order.refresh_from_db()
    assert order.status == "cancelled"
    assert stock_of(variant).reserved == 0


def test_customer_can_cancel_unpaid_order(auth_client, user, variant, cart):
    order = place(user)
    data = auth_client.post(f"{ORDERS}{order.number}/cancel/").json()
    assert data["status"] == "cancelled"
    assert stock_of(variant).reserved == 0


def test_mark_paid_deducts_stock_once_and_emails(user, variant, cart, django_capture_on_commit_callbacks):
    voucher = Voucher.objects.create(code="TEN", value=Decimal("10"))
    order = services.place_order(user, {**checkout_payload(), "voucher_code": "TEN"})

    with django_capture_on_commit_callbacks(execute=True):
        services.mark_paid(order)
        services.mark_paid(order)

    order.refresh_from_db()
    stock = stock_of(variant)
    voucher.refresh_from_db()
    assert order.status == "paid"
    assert (stock.quantity, stock.reserved) == (6, 0)
    assert voucher.used_count == 1
    assert len(mail.outbox) == 1
    assert order.number in mail.outbox[0].subject


def test_mark_paid_schedules_one_invoice_task_after_commit(
    user, variant, cart, django_capture_on_commit_callbacks
):
    order = services.place_order(user, checkout_payload())

    with (
        patch("apps.orders.services._notify"),
        django_capture_on_commit_callbacks(execute=True) as callbacks,
    ):
        services.mark_paid(order)
        services.mark_paid(order)

    assert len(callbacks) == 1
    invoice = Invoice.objects.get(order=order)
    assert invoice.status == Invoice.Status.FAILED


def test_paid_order_keeps_a_retryable_invoice_if_task_enqueue_fails(
    user, variant, cart, django_capture_on_commit_callbacks, caplog
):
    order = services.place_order(user, checkout_payload())

    with (
        patch("apps.orders.services._notify"),
        patch(
            "apps.invoicing.tasks.issue_invoice_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ),
    ):
        with django_capture_on_commit_callbacks(execute=True):
            services.mark_paid(order)

    invoice = Invoice.objects.get(order=order)
    assert invoice.status == Invoice.Status.PENDING
    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert "broker unavailable" in caplog.text


def test_paid_order_survives_confirmation_email_failure(
    user, variant, cart, django_capture_on_commit_callbacks, caplog
):
    order = services.place_order(user, checkout_payload())

    with (
        patch(
            "apps.notifications.tasks.send_order_confirmation.delay",
            side_effect=UnicodeEncodeError("charmap", "ț", 0, 1, "undefined"),
        ),
        patch("apps.invoicing.tasks.issue_invoice_task.delay") as issue_delay,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            services.mark_paid(order)

    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    issue_delay.assert_called_once_with(str(order.pk))
    assert "charmap" in caplog.text


def test_paid_garage_order_books_appointment_and_notifies_garage(user, cart, django_capture_on_commit_callbacks):
    garage = make_garage(email="garage@example.com")
    order = services.place_order(
        user,
        {
            **checkout_payload(),
            "delivery_method": "garage_fitting",
            "garage": garage,
            "slot_start": future_slot(garage),
        },
    )
    with django_capture_on_commit_callbacks(execute=True):
        services.mark_paid(order)

    assert Appointment.objects.get(order=order).status == "booked"
    assert {tuple(m.to) for m in mail.outbox} == {("ana@example.com",), ("garage@example.com",)}
    garage_mail = next(m for m in mail.outbox if m.to == ["garage@example.com"])
    local_start = timezone.localtime(Appointment.objects.get(order=order).slot_start)
    assert f"{local_start:%H:%M}" in garage_mail.subject


def test_payment_after_expiry_still_marks_paid(user, variant, cart):
    order = place(user)
    services.cancel_order(order, note="expired")

    services.mark_paid(order)

    order.refresh_from_db()
    assert order.status == "paid"
    assert stock_of(variant).quantity == 6
    # Looked up by status: on Windows the three changes can share the same created_at timestamp.
    assert "expired" in order.status_changes.get(status="paid").note


def test_late_payment_after_expiry_does_not_double_book_taken_garage_slot(user, variant, cart):
    garage = make_garage(capacity_per_slot=1)
    slot = future_slot(garage)
    payload = {
        **checkout_payload(),
        "delivery_method": "garage_fitting",
        "garage": garage,
        "slot_start": slot,
    }
    first_order = services.place_order(user, payload)
    services.cancel_order(first_order, note="expired")

    # Another customer books the same slot while first_order is cancelled
    other = User.objects.create_user(email="other-slot@example.com", password="x")
    add_to_cart(other, variant, 4)
    second_order = services.place_order(other, payload)

    # Late webhook arrives for first_order
    services.mark_paid(first_order)

    assert Appointment.objects.get(order=second_order).status == "held"
    assert Appointment.objects.get(order=first_order).status == "cancelled"
    assert "reschedule" in first_order.status_changes.get(status="paid").note


def test_staff_status_transitions(user, cart, django_capture_on_commit_callbacks):
    order = place(user)
    services.mark_paid(order)

    with django_capture_on_commit_callbacks(execute=True):
        services.change_status(order, Order.Status.PROCESSING)
        services.change_status(order, Order.Status.SHIPPED)

    order.refresh_from_db()
    assert order.status == "shipped"
    assert len(mail.outbox) == 2
    with pytest.raises(ValidationError):
        services.change_status(order, Order.Status.PROCESSING)


def test_cancelling_paid_order_restocks(user, variant, cart):
    order = place(user)
    services.mark_paid(order)

    services.change_status(order, Order.Status.CANCELLED)

    assert stock_of(variant).quantity == 10


def test_cash_on_delivery_order(user, variant, cart):
    payload = checkout_payload(payment_method="cash_on_delivery")
    order = services.place_order(user, payload)

    assert order.status == Order.Status.CONFIRMED
    assert order.payment_method == Order.PaymentMethod.CASH_ON_DELIVERY
    assert order.reserved_until is None
    # Stock deducted immediately for COD
    assert stock_of(variant).quantity == 6
    assert stock_of(variant).reserved == 0

    # Staff workflow
    services.change_status(order, Order.Status.PROCESSING)
    services.change_status(order, Order.Status.SHIPPED)
    services.change_status(order, Order.Status.COMPLETED)

    order.refresh_from_db()
    assert order.status == Order.Status.COMPLETED
    assert order.paid_at is not None


def test_retour_restores_stock(user, variant, cart):
    payload = checkout_payload(payment_method="cash_on_delivery")
    order = services.place_order(user, payload)
    assert stock_of(variant).quantity == 6

    services.change_status(order, Order.Status.PROCESSING)
    services.change_status(order, Order.Status.SHIPPED)
    services.change_status(order, Order.Status.RETURNED)

    order.refresh_from_db()
    assert order.status == Order.Status.RETURNED
    # Stock restored back on the shelf
    assert stock_of(variant).quantity == 10


def test_place_order_reserves_and_releases_voucher(user, cart):
    voucher = Voucher.objects.create(code="REV10", value=Decimal("10"), max_uses=1, min_order_total=Decimal("500"))
    payload = checkout_payload(voucher_code="REV10")
    order = services.place_order(user, payload)

    voucher.refresh_from_db()
    assert voucher.reserved_count == 1
    assert voucher.used_count == 0

    services.cancel_order(order, note="Customer cancelled")
    voucher.refresh_from_db()
    assert voucher.reserved_count == 0
    assert voucher.used_count == 0
