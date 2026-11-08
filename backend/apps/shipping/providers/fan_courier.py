"""
FAN Courier API v2 (api.fancourier.ro). FAN shares its JSON spec on request only; endpoints follow
the widely used shusaura85/fancourier-api SDK: POST /login → Bearer token; POST /intern-awb;
GET /awb/label; GET /reports/awb/tracking. Verify against FAN's spec before going live.
"""

import math
from decimal import Decimal

import requests
from django.conf import settings

from apps.orders.models import Order

from .base import (
    TIMEOUT_SECONDS,
    AwbResult,
    CarrierAmbiguousError,
    CarrierProvider,
    CarrierRejectedError,
    TrackingUpdate,
    classify_carrier_status,
    ensure_pdf,
    error_text,
    require,
    safe_json,
    shipping_mode,
    total_weight,
    tracking_url,
)

DEFAULT_HOST = "https://api.fancourier.ro"


class FanCourierProvider(CarrierProvider):
    name = "fan_courier"
    display_name = "FAN Courier"

    def __init__(self):
        self._token: str | None = None

    @property
    def base_url(self) -> str:
        shipping_mode()  # FAN has no separate sandbox host; sandbox means a FAN test account.
        return (settings.FAN_COURIER_API_BASE_URL or "").strip().rstrip("/") or DEFAULT_HOST

    @property
    def client_id(self) -> str:
        return str(settings.FAN_COURIER_CLIENT_ID).strip()

    def _authenticate(self) -> str:
        if self._token:
            return self._token
        require(
            settings.FAN_COURIER_CLIENT_ID,
            settings.FAN_COURIER_USERNAME,
            settings.FAN_COURIER_PASSWORD,
            message="FAN_COURIER_CLIENT_ID, FAN_COURIER_USERNAME and FAN_COURIER_PASSWORD are required.",
        )
        url = f"{self.base_url}/login"
        body = self._login_request(
            lambda: requests.post(
                url,
                json={"username": settings.FAN_COURIER_USERNAME, "password": settings.FAN_COURIER_PASSWORD},
                timeout=TIMEOUT_SECONDS,
            )
        )
        data = body.get("data") if isinstance(body, dict) else None
        token = data.get("token") if isinstance(data, dict) else None
        if not token:
            raise CarrierRejectedError("FAN Courier login returned no token.")
        self._token = token
        return token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._authenticate()}"}

    def create_awb(self, order: Order, *, parcels: list[Decimal]) -> AwbResult:
        headers = self._headers()
        shipment = {
            "info": {
                "service": settings.FAN_COURIER_SERVICE or "Standard",
                "packages": {"parcel": len(parcels), "envelope": 0},
                "weight": max(1, math.ceil(total_weight(parcels))),
                "cod": 0,
                "declaredValue": 0,
                "payment": "expeditor",
                "observation": order.number,
                "content": "Wheels / tires",
            },
            "recipient": {
                "name": order.full_name,
                "phone": order.phone,
                "email": order.email,
                "address": {
                    "county": order.county,
                    "locality": order.city,
                    "street": order.line1,
                    "streetNo": "",
                    "zipCode": order.postal_code,
                    "apartment": order.line2,
                },
            },
        }
        try:
            response = requests.post(
                f"{self.base_url}/intern-awb",
                headers=headers,
                json={"clientId": self.client_id, "shipments": [shipment]},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise CarrierAmbiguousError(
                f"FAN Courier did not answer the AWB request; search order {order.number} in SelfAWB."
            ) from exc

        body = safe_json(response)
        if 400 <= response.status_code < 500:
            raise CarrierRejectedError(error_text(body, f"FAN Courier rejected the AWB (HTTP {response.status_code})."))
        results = body.get("response") if isinstance(body, dict) and 200 <= response.status_code < 300 else None
        first = results[0] if isinstance(results, list) and results and isinstance(results[0], dict) else None
        if first and first.get("errors"):
            raise CarrierRejectedError(error_text(first["errors"], "FAN Courier rejected the AWB."))
        awb = first.get("awbNumber") if first else None
        if not awb:
            raise CarrierAmbiguousError(
                f"FAN Courier returned an unclear AWB response; search order {order.number} in SelfAWB."
            )
        awb = str(awb)
        return AwbResult(awb=awb, tracking_url=tracking_url(settings.FAN_COURIER_TRACKING_URL, awb))

    def download_label(self, awb: str) -> bytes:
        headers = self._headers()
        params = {"clientId": self.client_id, "awbs[]": awb, "pdf": 1}
        response = self._read_request(
            lambda: requests.get(f"{self.base_url}/awb/label", headers=headers, params=params, timeout=TIMEOUT_SECONDS),
            "label",
        )
        return ensure_pdf(response, self.display_name)

    def track(self, awb: str) -> TrackingUpdate:
        headers = self._headers()
        params = {"clientId": self.client_id, "awb[]": awb, "language": "ro"}
        response = self._read_request(
            lambda: requests.get(
                f"{self.base_url}/reports/awb/tracking", headers=headers, params=params, timeout=TIMEOUT_SECONDS
            ),
            "tracking",
        )
        body = safe_json(response)
        data = body.get("data") if isinstance(body, dict) else None
        entry = data[0] if isinstance(data, list) and data and isinstance(data[0], dict) else {}
        events = entry.get("events") or []
        if not events:
            return TrackingUpdate(status=None, label="")
        label = str(events[-1].get("name") or "")
        return TrackingUpdate(status=classify_carrier_status(label), label=label[:120])
