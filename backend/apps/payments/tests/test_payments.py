import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments.models import Payment, WebhookEvent
from tests.factories import add_to_cart, checkout_payload, make_product, make_variant

pytestmark = pytest.mark.django_db

WEBHOOK = "/api/v1/payments/webhook/stripe/"
NETOPIA_WEBHOOK = "/api/v1/payments/webhook/netopia/"
SECRET = "whsec_test_secret"  # same as config/settings/test.py
NETOPIA_POS_SIGNATURE = "sandbox-pos-signature"


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


# --- NETOPIA ----------------------------------------------------------------------


def _netopia_provider(settings):
    from apps.payments.providers import get_provider

    settings.PAYMENT_PROVIDER = "netopia"
    settings.NETOPIA_MODE = "sandbox"
    settings.NETOPIA_API_KEY = "sandbox-api-key"
    settings.NETOPIA_POS_SIGNATURE = "sandbox-pos-signature"
    settings.NETOPIA_NOTIFY_URL = "https://api.example.test/api/v1/payments/webhook/netopia/"
    try:
        return get_provider()
    except KeyError:
        pytest.fail("PAYMENT_PROVIDER=netopia must resolve to the NETOPIA adapter")


def _netopia_response(payload, *, status_code=200):
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload).encode()
    return response


def test_netopia_checkout_uses_sandbox_credentials_and_maps_hosted_session(settings, order):
    provider = _netopia_provider(settings)
    response = _netopia_response(
        {
            "payment": {
                "ntpID": "ntp_123",
                "amount": 825.0,
                "currency": "RON",
                "paymentURL": "https://secure.sandbox.netopia-payments.com/pay/123",
            }
        }
    )
    with patch("requests.post", return_value=response) as post:
        session = provider.create_checkout(order)

    assert session.session_id == "ntp_123"
    assert session.url == "https://secure.sandbox.netopia-payments.com/pay/123"
    assert post.call_args.args[0] == "https://secure.sandbox.netopia-payments.com/payment/card/start"
    assert post.call_args.kwargs["headers"]["Authorization"] == "sandbox-api-key"
    payload = post.call_args.kwargs["json"]
    assert payload["config"]["notifyUrl"] == settings.NETOPIA_NOTIFY_URL
    assert payload["config"]["redirectUrl"] == f"http://localhost:5173/checkout/success?order={order.number}"
    assert payload["order"]["posSignature"] == "sandbox-pos-signature"
    assert payload["order"]["orderID"] == order.number
    assert payload["order"]["amount"] == 825.0
    assert payload["order"]["currency"] == "RON"


def test_netopia_checkout_persists_provider_session_from_order_payment_flow(auth_client, settings, order):
    _netopia_provider(settings)
    response = _netopia_response(
        {
            "payment": {
                "ntpID": "ntp_456",
                "amount": 825.0,
                "currency": "RON",
                "paymentURL": "https://secure.sandbox.netopia-payments.com/pay/456",
            }
        }
    )
    with patch("requests.post", return_value=response):
        result = auth_client.post(f"/api/v1/orders/{order.number}/pay/")

    assert result.status_code == 200
    assert result.json()["checkout_url"] == "https://secure.sandbox.netopia-payments.com/pay/456"
    payment = Payment.objects.get(order=order)
    assert (payment.provider, payment.session_id, payment.amount, payment.currency) == (
        "netopia",
        "ntp_456",
        order.total,
        "RON",
    )


def test_unconfigured_netopia_checkout_fails_without_fake_fallback(auth_client, settings, order):
    settings.PAYMENT_PROVIDER = "netopia"
    settings.NETOPIA_MODE = "sandbox"
    settings.NETOPIA_API_KEY = ""
    settings.NETOPIA_POS_SIGNATURE = ""
    settings.NETOPIA_NOTIFY_URL = ""
    with patch("requests.post") as post:
        result = auth_client.post(f"/api/v1/orders/{order.number}/pay/")

    assert result.status_code == 502
    assert result.json()["error"]["code"] == "payment_provider_error"
    assert Payment.objects.filter(order=order).count() == 0
    post.assert_not_called()


@pytest.fixture
def netopia_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem.decode()


def _netopia_callback_payload(order, *, status=3, amount=825.0, currency="RON", installments=3):
    return {
        "payment": {
            "method": "card",
            "ntpID": "ntp_123",
            "status": status,
            "amount": amount,
            "currency": currency,
            "options": {"installments": installments},
            "token": "",
            "data": {},
        },
        "order": {"orderID": order.number, "data": {}},
    }


def _netopia_callback_claims(raw_payload, *, audience=NETOPIA_POS_SIGNATURE):
    now = int(time.time())
    return {
        "iss": "NETOPIA Payments",
        "aud": audience,
        "sub": base64.b64encode(hashlib.sha512(raw_payload).digest()).decode(),
        "iat": now,
        "nbf": now - 1,
        "exp": now + 300,
    }


def _sign_netopia_callback(payload, private_key, *, audience=NETOPIA_POS_SIGNATURE):
    raw_payload = json.dumps(payload, separators=(",", ":")).encode()
    token = jwt.encode(
        _netopia_callback_claims(raw_payload, audience=audience),
        private_key,
        algorithm="RS512",
    )
    return raw_payload, token


def _configure_netopia_webhook(settings, public_key):
    settings.NETOPIA_POS_SIGNATURE = NETOPIA_POS_SIGNATURE
    settings.NETOPIA_POS_SIGNATURE_SET = [NETOPIA_POS_SIGNATURE]
    settings.NETOPIA_PUBLIC_KEY = public_key


def _create_netopia_payment(order, *, amount=None, currency="RON"):
    return Payment.objects.create(
        order=order,
        provider="netopia",
        session_id="ntp_123",
        amount=order.total if amount is None else amount,
        currency=currency,
    )


@pytest.mark.parametrize("provider_status", [3, 5])
def test_netopia_webhook_marks_paid_once_and_maps_installments(
    api_client, settings, order, netopia_keypair, provider_status
):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    payload, token = _sign_netopia_callback(
        _netopia_callback_payload(order, status=provider_status),
        private_key,
    )

    with patch("apps.payments.services.mark_paid", wraps=order_services.mark_paid) as mark_paid:
        for _ in range(2):
            response = api_client.post(
                NETOPIA_WEBHOOK,
                data=payload,
                content_type="application/json",
                HTTP_VERIFICATION_TOKEN=token,
            )
            assert response.status_code == 200

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.SUCCEEDED
    assert payment.installments == 3
    assert order.status == Order.Status.PAID
    assert WebhookEvent.objects.filter(provider="netopia").count() == 1
    assert mark_paid.call_count == 1


def test_netopia_webhook_accepts_escaped_public_key_newlines(api_client, settings, order, netopia_keypair):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key.replace("\n", "\\n"))
    _create_netopia_payment(order)
    payload, token = _sign_netopia_callback(_netopia_callback_payload(order), private_key)

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == Order.Status.PAID


def test_netopia_webhook_rejects_bad_signature_without_changing_payment(api_client, settings, order, netopia_keypair):
    _, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    wrong_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    ).private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    payload, token = _sign_netopia_callback(_netopia_callback_payload(order), wrong_private_key)

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 400
    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.CREATED
    assert order.status == Order.Status.PENDING_PAYMENT
    assert WebhookEvent.objects.filter(provider="netopia").count() == 0


def test_netopia_webhook_rejects_unexpected_jwt_algorithm(api_client, settings, order, netopia_keypair):
    _, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    raw_payload = json.dumps(_netopia_callback_payload(order), separators=(",", ":")).encode()
    token = jwt.encode(
        _netopia_callback_claims(raw_payload),
        "attacker-controlled-key-with-at-least-thirty-two-bytes",
        algorithm="HS256",
    )

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=raw_payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 400
    payment.refresh_from_db()
    assert payment.status == Payment.Status.CREATED


def test_netopia_webhook_rejects_missing_verification_token(api_client, settings, order, netopia_keypair):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    payload, _ = _sign_netopia_callback(_netopia_callback_payload(order), private_key)

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 400
    payment.refresh_from_db()
    assert payment.status == Payment.Status.CREATED


def test_netopia_webhook_requires_pos_signature_in_allowlist(api_client, settings, order, netopia_keypair):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    settings.NETOPIA_POS_SIGNATURE_SET = ["another-pos-signature"]
    payment = _create_netopia_payment(order)
    payload, token = _sign_netopia_callback(_netopia_callback_payload(order), private_key)

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 400
    payment.refresh_from_db()
    assert payment.status == Payment.Status.CREATED
    assert WebhookEvent.objects.filter(provider="netopia").count() == 0


def test_netopia_webhook_requires_matching_pos_audience(api_client, settings, order, netopia_keypair):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    payload, token = _sign_netopia_callback(
        _netopia_callback_payload(order),
        private_key,
        audience="another-pos-signature",
    )

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 400
    payment.refresh_from_db()
    assert payment.status == Payment.Status.CREATED


def test_netopia_webhook_fails_closed_without_public_key(api_client, settings, order, netopia_keypair):
    private_key, _ = netopia_keypair
    settings.NETOPIA_POS_SIGNATURE = NETOPIA_POS_SIGNATURE
    settings.NETOPIA_POS_SIGNATURE_SET = [NETOPIA_POS_SIGNATURE]
    settings.NETOPIA_PUBLIC_KEY = ""
    payment = _create_netopia_payment(order)
    payload, token = _sign_netopia_callback(_netopia_callback_payload(order), private_key)

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "netopia_webhook_configuration_error"
    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.CREATED
    assert order.status == Order.Status.PENDING_PAYMENT


def test_netopia_webhook_rejects_tampered_payload(api_client, settings, order, netopia_keypair):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    signed_payload, token = _sign_netopia_callback(_netopia_callback_payload(order), private_key)
    tampered_payload = signed_payload.replace(b'"amount":825.0', b'"amount":1.0')

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=tampered_payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 400
    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.CREATED
    assert order.status == Order.Status.PENDING_PAYMENT


@pytest.mark.parametrize(
    ("amount", "currency"),
    [(1.0, "RON"), (825.0, "EUR")],
)
def test_netopia_webhook_rejects_payment_mismatch(api_client, settings, order, netopia_keypair, amount, currency):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    payload, token = _sign_netopia_callback(
        _netopia_callback_payload(order, amount=amount, currency=currency),
        private_key,
    )

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 200
    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert order.status == Order.Status.PENDING_PAYMENT


def test_netopia_webhook_rejects_order_reference_mismatch(api_client, settings, order, netopia_keypair):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    payload_data = _netopia_callback_payload(order)
    payload_data["order"]["orderID"] = "OW-ANOTHER-ORDER"
    payload, token = _sign_netopia_callback(payload_data, private_key)

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 200
    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert order.status == Order.Status.PENDING_PAYMENT


@pytest.mark.parametrize("provider_status", [4, 12])
def test_netopia_webhook_records_cancelled_and_declined_payments(
    api_client, settings, order, netopia_keypair, provider_status
):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    payload, token = _sign_netopia_callback(
        _netopia_callback_payload(order, status=provider_status, installments=0),
        private_key,
    )

    response = api_client.post(
        NETOPIA_WEBHOOK,
        data=payload,
        content_type="application/json",
        HTTP_VERIFICATION_TOKEN=token,
    )

    assert response.status_code == 200
    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert order.status == Order.Status.PENDING_PAYMENT


def test_netopia_webhook_does_not_reverse_terminal_success(api_client, settings, order, netopia_keypair):
    private_key, public_key = netopia_keypair
    _configure_netopia_webhook(settings, public_key)
    payment = _create_netopia_payment(order)
    success_payload, success_token = _sign_netopia_callback(_netopia_callback_payload(order), private_key)
    cancelled_payload, cancelled_token = _sign_netopia_callback(
        _netopia_callback_payload(order, status=4, installments=0),
        private_key,
    )

    for payload, token in (
        (success_payload, success_token),
        (cancelled_payload, cancelled_token),
    ):
        response = api_client.post(
            NETOPIA_WEBHOOK,
            data=payload,
            content_type="application/json",
            HTTP_VERIFICATION_TOKEN=token,
        )
        assert response.status_code == 200

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == Payment.Status.SUCCEEDED
    assert order.status == Order.Status.PAID
    assert WebhookEvent.objects.filter(provider="netopia").count() == 2


def test_netopia_checkout_uses_live_endpoint_when_configured(settings, order):
    provider = _netopia_provider(settings)
    settings.NETOPIA_MODE = "live"
    response = _netopia_response(
        {
            "payment": {
                "ntpID": "ntp_live_123",
                "amount": 825.0,
                "currency": "RON",
                "paymentURL": "https://secure.mobilpay.ro/pay/123",
            }
        }
    )
    with patch("requests.post", return_value=response) as post:
        provider.create_checkout(order)

    assert post.call_args.args[0] == "https://secure.mobilpay.ro/pay/payment/card/start"


@pytest.mark.parametrize(
    ("amount", "currency"),
    [(1.0, "RON"), (825.0, "EUR")],
)
def test_netopia_checkout_rejects_mismatched_provider_amount_or_currency(settings, order, amount, currency):
    provider = _netopia_provider(settings)
    response = _netopia_response(
        {
            "payment": {
                "ntpID": "ntp_mismatch",
                "amount": amount,
                "currency": currency,
                "paymentURL": "https://secure.sandbox.netopia-payments.com/pay/mismatch",
            }
        }
    )
    with patch("requests.post", return_value=response):
        with pytest.raises(APIException, match="NETOPIA"):
            provider.create_checkout(order)


def test_netopia_checkout_rejects_malformed_provider_response(settings, order):
    provider = _netopia_provider(settings)
    response = _netopia_response({"payment": {"ntpID": "ntp_123"}})
    with patch("requests.post", return_value=response):
        with pytest.raises(APIException, match="NETOPIA"):
            provider.create_checkout(order)


def test_netopia_checkout_rejects_malformed_hosted_url(settings, order):
    provider = _netopia_provider(settings)
    response = _netopia_response({"payment": {"ntpID": "ntp_123", "paymentURL": "https://["}})
    with patch("requests.post", return_value=response):
        with pytest.raises(APIException, match="NETOPIA"):
            provider.create_checkout(order)


def test_netopia_checkout_rejects_malformed_notification_url(settings, order):
    provider = _netopia_provider(settings)
    settings.NETOPIA_NOTIFY_URL = "https://["
    with patch("requests.post") as post:
        with pytest.raises(APIException, match="NETOPIA"):
            provider.create_checkout(order)

    post.assert_not_called()


def test_netopia_checkout_surfaces_provider_timeout(settings, order):
    provider = _netopia_provider(settings)
    with patch("requests.post", side_effect=requests.Timeout("timed out")):
        with pytest.raises(APIException, match="NETOPIA"):
            provider.create_checkout(order)


def test_netopia_checkout_surfaces_provider_http_error(settings, order):
    provider = _netopia_provider(settings)
    response = _netopia_response({"error": {"message": "invalid request"}}, status_code=503)
    with patch("requests.post", return_value=response):
        with pytest.raises(APIException, match="NETOPIA"):
            provider.create_checkout(order)


def test_netopia_checkout_rejects_error_payload_even_with_payment_url(settings, order):
    provider = _netopia_provider(settings)
    response = _netopia_response(
        {
            "error": {"code": "invalid_order", "message": "Invalid order"},
            "payment": {
                "ntpID": "ntp_error",
                "amount": 825.0,
                "currency": "RON",
                "paymentURL": "https://secure.sandbox.netopia-payments.com/pay/error",
            },
        }
    )
    with patch("requests.post", return_value=response):
        with pytest.raises(APIException, match="NETOPIA"):
            provider.create_checkout(order)
