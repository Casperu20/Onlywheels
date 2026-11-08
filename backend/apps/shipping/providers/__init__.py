from django.conf import settings

from .base import (
    AwbResult,
    CarrierAmbiguousError,
    CarrierConfigurationError,
    CarrierError,
    CarrierProvider,
    CarrierRejectedError,
    TrackingUpdate,
    classify_carrier_status,
)
from .demo import DemoProvider
from .fan_courier import FanCourierProvider
from .sameday import SamedayProvider

PROVIDERS = {
    SamedayProvider.name: SamedayProvider,
    FanCourierProvider.name: FanCourierProvider,
    DemoProvider.name: DemoProvider,
}


def get_carrier_provider(carrier: str | None = None) -> CarrierProvider:
    carrier = (carrier or settings.SHIPPING_CARRIER or "").strip().lower()
    if not carrier:
        raise CarrierConfigurationError("Courier integration is disabled (SHIPPING_CARRIER is empty).")
    if carrier not in PROVIDERS:
        raise CarrierConfigurationError(
            f"Unknown SHIPPING_CARRIER '{carrier}'; use 'sameday', 'fan_courier' or 'demo'."
        )
    return PROVIDERS[carrier]()


__all__ = [
    "AwbResult",
    "CarrierAmbiguousError",
    "CarrierConfigurationError",
    "CarrierError",
    "CarrierProvider",
    "CarrierRejectedError",
    "DemoProvider",
    "FanCourierProvider",
    "SamedayProvider",
    "TrackingUpdate",
    "classify_carrier_status",
    "get_carrier_provider",
]
