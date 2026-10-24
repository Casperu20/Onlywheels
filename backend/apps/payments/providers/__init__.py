from django.conf import settings

from .base import CheckoutSession, PaymentProvider
from .fake import FakeProvider
from .stripe_provider import StripeProvider

PROVIDERS: dict[str, type[PaymentProvider]] = {
    "fake": FakeProvider,
    "stripe": StripeProvider,
}


def get_provider() -> PaymentProvider:
    return PROVIDERS[settings.PAYMENT_PROVIDER]()


__all__ = ["CheckoutSession", "PaymentProvider", "get_provider"]
