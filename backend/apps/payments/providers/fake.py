import uuid

from django.conf import settings

from apps.orders.models import Order

from .base import CheckoutSession, PaymentProvider


class FakeProvider(PaymentProvider):
    """Development only: sends the customer to a frontend page that simulates the payment."""

    name = "fake"

    def create_checkout(self, order: Order) -> CheckoutSession:
        return CheckoutSession(
            session_id=f"fake_{uuid.uuid4().hex}",
            url=f"{settings.FRONTEND_URL}/checkout/fake-pay?order={order.number}",
        )
