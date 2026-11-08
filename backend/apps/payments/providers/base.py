from abc import ABC, abstractmethod
from dataclasses import dataclass

from rest_framework.exceptions import APIException

from apps.orders.models import Order


@dataclass(frozen=True)
class CheckoutSession:
    session_id: str
    url: str


class PaymentProviderError(APIException):
    status_code = 502
    default_detail = "Payment provider could not start checkout."
    default_code = "payment_provider_error"


class PaymentProvider(ABC):
    """A hosted payment page: we redirect the customer there and get the result via webhook."""

    name: str

    @abstractmethod
    def create_checkout(self, order: Order) -> CheckoutSession: ...
