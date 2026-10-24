import hashlib
import hmac
import json
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments.models import Payment, WebhookEvent
from tests.factories import add_to_cart, checkout_payload, make_product, make_variant

pytestmark = pytest.mark.django_db

WEBHOOK = "/api/v1/payments/webhook/stripe/"
SECRET = "whsec_test_secret"  # same as config/settings/test.py


@pytest.fixture
def order(user) -> Order:
    add_to_cart(user, make_variant(make_product(), price="200"), 4)
    return order_services.place_order(user, checkout_payload())  # total 825.00


def sign(payload: str, secret: str = SECRET) -> str:
    timestamp = int(time.time())
    signature = hmac.new(secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def stripe_event(session_id: str, *, amount: int = 82500, event_id: str = "evt_1") -> str:
    return json.dumps(
        {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": session_id,
                    "payment_status": "paid",
                    "amount_total": amount,
                    "currency": "ron",
                    "payment_intent": "pi_123",
                }
            },
        }
    )


# --- Fake provider (development) ---------------------------------------------


def test_fake_payment_flow(auth_client, order):
    response = auth_client.post(f"/api/v1/orders/{order.number}/pay/")
    assert response.status_code == 200
    assert f"/checkout/fake-pay?order={order.number}" in response.json()["checkout_url"]

    response = auth_client.post("/api/v1/payments/fake/complete/", {"order_number": order.number}, format="json")
    assert response.json() == {"status": "paid"}
    assert Payment.objects.get().status == "succeeded"


def test_fake_completion_disabled_for_real_providers(auth_client, order, settings):
    settings.PAYMENT_PROVIDER = "stripe"
    response = auth_client.post("/api/v1/payments/fake/complete/", {"order_number": order.number}, format="json")
    assert response.status_code == 404


def test_cannot_pay_expired_order(auth_client, order):
    Order.objects.filter(pk=order.pk).update(reserved_until=timezone.now() - timedelta(seconds=1))
    assert auth_client.post(f"/api/v1/orders/{order.number}/pay/").status_code == 400


# --- Stripe -----------------------------------------------------------------------


@pytest.fixture
def stripe_payment(auth_client, order, settings) -> Payment:
    settings.PAYMENT_PROVIDER = "stripe"
    session = SimpleNamespace(id="cs_test_1", url="https://checkout.stripe.com/c/pay/cs_test_1")
    with patch("stripe.checkout.Session.create", return_value=session) as create:
        response = auth_client.post(f"/api/v1/orders/{order.number}/pay/")
    assert response.json()["checkout_url"] == session.url
    assert create.call_args.kwargs["line_items"][0]["price_data"]["unit_amount"] == 82500
    return Payment.objects.get(session_id="cs_test_1")


def test_stripe_webhook_marks_order_paid_once(api_client, stripe_payment):
    payload = stripe_event("cs_test_1")
    for _ in range(2):  # Stripe may deliver the same event twice
        response = api_client.post(
            WEBHOOK, data=payload, content_type="application/json", HTTP_STRIPE_SIGNATURE=sign(payload)
        )
        assert response.status_code == 200

    stripe_payment.refresh_from_db()
    assert stripe_payment.status == "succeeded"
    assert stripe_payment.order.status == "paid"
    assert WebhookEvent.objects.count() == 1


def test_stripe_webhook_rejects_bad_signature(api_client, stripe_payment):
    payload = stripe_event("cs_test_1")
    response = api_client.post(
        WEBHOOK, data=payload, content_type="application/json", HTTP_STRIPE_SIGNATURE=sign(payload, "wrong")
    )
    assert response.status_code == 400
    stripe_payment.order.refresh_from_db()
    assert stripe_payment.order.status == "pending_payment"


def test_stripe_webhook_rejects_amount_mismatch(api_client, stripe_payment):
    payload = stripe_event("cs_test_1", amount=100)
    api_client.post(WEBHOOK, data=payload, content_type="application/json", HTTP_STRIPE_SIGNATURE=sign(payload))

    stripe_payment.refresh_from_db()
    assert stripe_payment.status == "failed"
    assert stripe_payment.order.status == "pending_payment"
