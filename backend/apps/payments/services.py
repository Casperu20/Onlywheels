import base64
import hashlib
import hmac
import json
import logging
from collections.abc import Mapping
from decimal import Decimal
from json import JSONDecodeError

import jwt
import stripe
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from apps.orders.models import Order
from apps.orders.services import mark_paid

from .models import Payment, WebhookEvent
from .providers import CheckoutSession, get_provider
from .providers.stripe_provider import to_minor_units

logger = logging.getLogger(__name__)


def start_checkout(order: Order) -> CheckoutSession:
    provider = get_provider()
    session = provider.create_checkout(order)
    Payment.objects.create(
        order=order,
        provider=provider.name,
        session_id=session.session_id,
        amount=order.total,
        currency=order.currency,
    )
    return session


def complete_fake_payment(order: Order) -> Order:
    """Development shortcut that behaves like a successful provider webhook."""
    payment = order.payments.filter(provider="fake", status=Payment.Status.CREATED).first()
    if payment is None:
        raise ValidationError({"non_field_errors": ["Start the payment first."]})
    payment.status = Payment.Status.SUCCEEDED
    payment.save(update_fields=["status", "updated_at"])
    return mark_paid(order, note="Payment received (simulated)")


# --- Stripe -----------------------------------------------------------------


def verify_stripe_event(payload: bytes, signature: str) -> dict:
    """Raises ValueError / stripe.SignatureVerificationError if the request is not from Stripe."""
    stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
    return json.loads(payload)


@transaction.atomic
def handle_stripe_event(event: dict) -> None:
    _, created = WebhookEvent.objects.get_or_create(
        provider="stripe", event_id=event["id"], defaults={"type": event["type"]}
    )
    if not created:
        return  # already processed (Stripe retries deliveries)

    session = event["data"]["object"]
    event_type = event["type"]
    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if session.get("payment_status") == "paid":
            _session_paid(session)
    elif event_type == "checkout.session.expired":
        _set_status(session, Payment.Status.EXPIRED)
    elif event_type == "checkout.session.async_payment_failed":
        _set_status(session, Payment.Status.FAILED, "Asynchronous payment failed")


def _payment_for(session: dict) -> Payment | None:
    payment = (
        Payment.objects.select_related("order")
        .filter(provider="stripe", session_id=session.get("id"))
        .first()
    )
    if payment is None:
        logger.warning("Stripe session %s does not match any payment", session.get("id"))
    return payment


def _set_status(session: dict, status: str, reason: str = "") -> None:
    payment = _payment_for(session)
    if payment and payment.status == Payment.Status.CREATED:
        payment.status = status
        payment.failure_reason = reason
        payment.save(update_fields=["status", "failure_reason", "updated_at"])


def _session_paid(session: dict) -> None:
    payment = _payment_for(session)
    if payment is None:
        return
    amount_ok = session.get("amount_total") == to_minor_units(payment.amount)
    currency_ok = (session.get("currency") or "").upper() == payment.currency.upper()
    if not (amount_ok and currency_ok):
        logger.error("Stripe amount/currency mismatch for order %s", payment.order.number)
        _set_status(session, Payment.Status.FAILED, "Amount or currency mismatch")
        return

    payment.status = Payment.Status.SUCCEEDED
    payment.payment_reference = session.get("payment_intent") or ""
    payment.save(update_fields=["status", "payment_reference", "updated_at"])
    mark_paid(payment.order, note="Payment received (Stripe)")


class NetopiaWebhookConfigurationError(APIException):
    status_code = 503
    default_detail = "NETOPIA webhook verification is not configured."
    default_code = "netopia_webhook_configuration_error"


class NetopiaPaymentNotFound(APIException):
    status_code = 404
    default_detail = "NETOPIA payment reference was not found."
    default_code = "payment_not_found"


def verify_netopia_callback(payload: bytes, headers: Mapping[str, str]) -> dict:
    verification_token = next(
        (value for name, value in headers.items() if name.lower() == "verification-token"),
        "",
    )
    public_key = settings.NETOPIA_PUBLIC_KEY.replace("\\n", "\n").strip()
    pos_signature = settings.NETOPIA_POS_SIGNATURE.strip()
    configured_signatures = settings.NETOPIA_POS_SIGNATURE_SET
    if not public_key or not pos_signature or not configured_signatures:
        raise NetopiaWebhookConfigurationError()
    if not verification_token:
        raise ValueError("NETOPIA verification token is missing.")

    allowed_signatures = set(configured_signatures)
    try:
        claims = jwt.decode(
            verification_token,
            public_key,
            algorithms=["RS512"],
            options={"verify_aud": False, "verify_iss": False},
        )
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise ValueError("NETOPIA verification token is invalid.") from exc

    if claims.get("iss") != "NETOPIA Payments":
        raise ValueError("NETOPIA verification token issuer is invalid.")
    audience = claims.get("aud")
    audiences = [audience] if isinstance(audience, str) else audience
    if (
        not isinstance(audiences, list)
        or not audiences
        or not all(isinstance(value, str) for value in audiences)
        or pos_signature not in allowed_signatures
        or pos_signature not in audiences
        or not set(audiences).issubset(allowed_signatures)
    ):
        raise ValueError("NETOPIA verification token audience is invalid.")

    expected_hash = base64.b64encode(hashlib.sha512(payload).digest()).decode("ascii")
    payload_hash = claims.get("sub")
    if not isinstance(payload_hash, str) or not hmac.compare_digest(payload_hash, expected_hash):
        raise ValueError("NETOPIA callback payload hash is invalid.")

    try:
        event = json.loads(payload)
    except (JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("NETOPIA callback payload is invalid JSON.") from exc
    if not isinstance(event, dict):
        raise ValueError("NETOPIA callback payload must be an object.")

    payment = event.get("payment")
    order = event.get("order")
    if not isinstance(payment, dict) or not isinstance(order, dict):
        raise ValueError("NETOPIA callback is missing payment or order data.")
    if not isinstance(payment.get("ntpID"), str) or not payment["ntpID"].strip():
        raise ValueError("NETOPIA callback is missing its payment reference.")
    if type(payment.get("status")) is not int:
        raise ValueError("NETOPIA callback payment status is invalid.")
    amount = payment.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, int | float):
        raise ValueError("NETOPIA callback payment amount is invalid.")
    if not Decimal(str(amount)).is_finite():
        raise ValueError("NETOPIA callback payment amount is invalid.")
    if not isinstance(payment.get("currency"), str):
        raise ValueError("NETOPIA callback payment currency is invalid.")
    if not isinstance(order.get("orderID"), str) or not order["orderID"].strip():
        raise ValueError("NETOPIA callback is missing its order reference.")

    event["_event_id"] = hashlib.sha256(payload).hexdigest()
    event["_event_type"] = f"payment.status.{payment['status']}"
    return event


@transaction.atomic
def handle_netopia_event(event: dict) -> None:
    provider_payment = event["payment"]
    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .filter(provider="netopia", session_id=provider_payment["ntpID"])
        .first()
    )
    if payment is None:
        raise NetopiaPaymentNotFound()

    _, created = WebhookEvent.objects.get_or_create(
        provider="netopia",
        event_id=event["_event_id"],
        defaults={"type": event["_event_type"]},
    )
    if not created or payment.status != Payment.Status.CREATED:
        return

    provider_order = event["order"]
    if provider_order["orderID"] != payment.order.number:
        _fail_netopia_payment(payment, "NETOPIA order reference mismatch")
        logger.error("NETOPIA order reference mismatch for payment %s", payment.session_id)
        return

    amount_matches = Decimal(str(provider_payment["amount"])) == payment.amount
    currency_matches = provider_payment["currency"].upper() == payment.currency.upper()
    if not (amount_matches and currency_matches):
        _fail_netopia_payment(payment, "Amount or currency mismatch")
        logger.error("NETOPIA amount/currency mismatch for order %s", payment.order.number)
        return

    options = provider_payment.get("options")
    installments = options.get("installments") if isinstance(options, dict) else None
    if type(installments) is not int or installments < 0:
        installments = None

    provider_status = provider_payment["status"]
    if provider_status in (3, 5):
        payment.status = Payment.Status.SUCCEEDED
        payment.payment_reference = provider_payment.get("rrn") or ""
        if installments is not None:
            payment.installments = installments
        payment.save(update_fields=["status", "payment_reference", "installments", "updated_at"])
        mark_paid(payment.order, note="Payment received (NETOPIA)")
    elif provider_status in (4, 11, 12, 13, 23):
        payment.status = Payment.Status.EXPIRED if provider_status == 23 else Payment.Status.FAILED
        payment.failure_reason = f"NETOPIA payment status {provider_status}"
        if installments is not None:
            payment.installments = installments
        payment.save(update_fields=["status", "failure_reason", "installments", "updated_at"])
    elif installments is not None:
        payment.installments = installments
        payment.save(update_fields=["installments", "updated_at"])


def _fail_netopia_payment(payment: Payment, reason: str) -> None:
    payment.status = Payment.Status.FAILED
    payment.failure_reason = reason
    payment.save(update_fields=["status", "failure_reason", "updated_at"])
