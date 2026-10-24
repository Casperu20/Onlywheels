from abc import ABC, abstractmethod
from dataclasses import dataclass

from apps.orders.models import Order


@dataclass(frozen=True)
class AwbResult:
    awb: str
    label_pdf: bytes
    tracking_url: str


class CarrierProvider(ABC):
    name: str

    @abstractmethod
    def create_awb(self, order: Order, *, parcels: int, weight_kg: float) -> AwbResult: ...

    @abstractmethod
    def track(self, awb: str) -> str:
        """Return one of Shipment.Status values."""
