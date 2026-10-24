"""Fan Courier API v2 (api.fancourier.ro): POST /login → token; POST /intern-awb; GET /reports/awb/tracking."""

from apps.orders.models import Order

from .base import AwbResult, CarrierProvider


class FanCourierProvider(CarrierProvider):
    name = "fan_courier"

    def create_awb(self, order: Order, *, parcels: int, weight_kg: float) -> AwbResult:
        raise NotImplementedError("Phase 2")

    def track(self, awb: str) -> str:
        raise NotImplementedError("Phase 2")
