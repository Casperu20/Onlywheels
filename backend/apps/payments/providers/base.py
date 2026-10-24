from abc import ABC, abstractmethod
from dataclasses import dataclass

from apps.orders.models import Order


@dataclass(frozen=True)
class CheckoutSession:
    session_id: str
    url: str


class PaymentProvider(ABC):
    """A hosted payment page: we redirect the customer there and get the result via webhook."""

    name: str

    @abstractmethod
    def create_checkout(self, order: Order) -> CheckoutSession: ...
