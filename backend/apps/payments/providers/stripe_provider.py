from datetime import timedelta
from decimal import Decimal

import stripe
from django.conf import settings
from django.utils import timezone

from apps.orders.models import Order

from .base import CheckoutSession, PaymentProvider


def to_minor_units(amount: Decimal) -> int:
    """RON -> bani (Stripe expects integer amounts in the smallest currency unit)."""
    return int((amount * 100).quantize(Decimal("1")))


class StripeProvider(PaymentProvider):
    name = "stripe"

    def create_checkout(self, order: Order) -> CheckoutSession:
        frontend = settings.FRONTEND_URL
        session = stripe.checkout.Session.create(
            api_key=settings.STRIPE_SECRET_KEY,
            mode="payment",
            customer_email=order.email,
            client_reference_id=order.number,
            metadata={"order_number": order.number},
            payment_intent_data={"metadata": {"order_number": order.number}},
            line_items=[
                {
                    # One line for the whole order keeps vouchers/shipping/fitting consistent
                    # with our own totals; the detailed lines are on our invoice.
                    "quantity": 1,
                    "price_data": {
                        "currency": order.currency.lower(),
                        "unit_amount": to_minor_units(order.total),
                        "product_data": {"name": f"OnlyWheels order {order.number}"},
                    },
                }
            ],
            success_url=f"{frontend}/checkout/success?order={order.number}",
            cancel_url=f"{frontend}/account/orders/{order.number}?payment=cancelled",
            expires_at=int((timezone.now() + timedelta(minutes=30)).timestamp()),
        )
        return CheckoutSession(session_id=session.id, url=session.url)
