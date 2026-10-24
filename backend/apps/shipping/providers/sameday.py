"""Sameday API (api.sameday.ro): POST /api/authenticate → token; POST /api/awb; GET /api/client/awb/{awb}/status."""

from apps.orders.models import Order

from .base import AwbResult, CarrierProvider


class SamedayProvider(CarrierProvider):
    name = "sameday"

    def create_awb(self, order: Order, *, parcels: int, weight_kg: float) -> AwbResult:
        raise NotImplementedError("Phase 2")

    def track(self, awb: str) -> str:
        raise NotImplementedError("Phase 2")
