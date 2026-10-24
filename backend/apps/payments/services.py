import json
import logging

import stripe
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

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
