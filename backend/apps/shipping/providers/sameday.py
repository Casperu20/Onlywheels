"""
Sameday eAWB API, following the official sameday-courier/php-sdk:
POST /api/authenticate (X-AUTH-USERNAME/PASSWORD) → token sent as X-AUTH-TOKEN;
POST /api/awb (form-encoded); GET /api/awb/download/{awb}/A4; GET /api/client/awb/{awb}/status.
"""

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

HOSTS = {"sandbox": "https://sameday-api.demo.zitec.com", "live": "https://api.sameday.ro"}
PAYER_SHOP = 1  # AwbPaymentType::CLIENT — the shop pays shipping (orders are prepaid).
PACKAGE_PARCEL = 0
PERSON_INDIVIDUAL = 0


class SamedayProvider(CarrierProvider):
    name = "sameday"
    display_name = "Sameday"

    def __init__(self):
        self._token: str | None = None

    @property
    def base_url(self) -> str:
        override = (settings.SAMEDAY_API_BASE_URL or "").strip().rstrip("/")
        return override or HOSTS[shipping_mode()]

    def _authenticate(self) -> str:
        if self._token:
            return self._token
        require(
            settings.SAMEDAY_USERNAME,
            settings.SAMEDAY_PASSWORD,
            message="SAMEDAY_USERNAME and SAMEDAY_PASSWORD are required.",
        )
        url = f"{self.base_url}/api/authenticate"
        body = self._login_request(
            lambda: requests.post(
                url,
                headers={"X-AUTH-USERNAME": settings.SAMEDAY_USERNAME, "X-AUTH-PASSWORD": settings.SAMEDAY_PASSWORD},
                data={"remember_me": "true"},
                timeout=TIMEOUT_SECONDS,
            )
        )
        token = body.get("token") if isinstance(body, dict) else None
        if not token:
            raise CarrierRejectedError("Sameday login returned no token.")
        self._token = token
        return token

    def _headers(self) -> dict:
        return {"X-AUTH-TOKEN": self._authenticate()}

    def create_awb(self, order: Order, *, parcels: list[Decimal]) -> AwbResult:
        require(
            settings.SAMEDAY_PICKUP_POINT_ID,
            settings.SAMEDAY_SERVICE_ID,
            message="SAMEDAY_PICKUP_POINT_ID and SAMEDAY_SERVICE_ID are required.",
        )
        headers = self._headers()
        address = ", ".join(part for part in (order.line1, order.line2) if part)
        data = {
            "pickupPoint": settings.SAMEDAY_PICKUP_POINT_ID,
            "service": settings.SAMEDAY_SERVICE_ID,
            "packageType": PACKAGE_PARCEL,
            "packageNumber": len(parcels),
            "packageWeight": str(total_weight(parcels)),
            "awbPayment": PAYER_SHOP,
            "cashOnDelivery": 0,
            "insuredValue": 0,
            "thirdPartyPickup": 0,
            "clientInternalReference": order.number,
            "observation": f"OnlyWheels {order.number}",
            "awbRecipient[name]": order.full_name,
            "awbRecipient[phoneNumber]": order.phone,
            "awbRecipient[email]": order.email,
            "awbRecipient[personType]": PERSON_INDIVIDUAL,
            "awbRecipient[address]": address,
            "awbRecipient[cityString]": order.city,
            "awbRecipient[countyString]": order.county,
            "awbRecipient[postalCode]": order.postal_code,
        }
        for index, weight in enumerate(parcels):
            data[f"parcels[{index}][weight]"] = str(weight)

        try:
            response = requests.post(f"{self.base_url}/api/awb", headers=headers, data=data, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise CarrierAmbiguousError(
                f"Sameday did not answer the AWB request; search reference {order.number} in the Sameday portal."
            ) from exc

        body = safe_json(response)
        if 400 <= response.status_code < 500:
            raise CarrierRejectedError(error_text(body, f"Sameday rejected the AWB (HTTP {response.status_code})."))
        awb = body.get("awbNumber") if isinstance(body, dict) and 200 <= response.status_code < 300 else None
        if not awb:
            raise CarrierAmbiguousError(
                f"Sameday returned an unclear AWB response; search reference {order.number} in the Sameday portal."
            )
        awb = str(awb)
        return AwbResult(awb=awb, tracking_url=tracking_url(settings.SAMEDAY_TRACKING_URL, awb))

    def download_label(self, awb: str) -> bytes:
        headers = self._headers()
        response = self._read_request(
            lambda: requests.get(
                f"{self.base_url}/api/awb/download/{awb}/A4", headers=headers, timeout=TIMEOUT_SECONDS
            ),
            "label",
        )
        return ensure_pdf(response, self.display_name)

    def track(self, awb: str) -> TrackingUpdate:
        headers = self._headers()
        response = self._read_request(
            lambda: requests.get(
                f"{self.base_url}/api/client/awb/{awb}/status", headers=headers, timeout=TIMEOUT_SECONDS
            ),
            "tracking",
        )
        body = safe_json(response)
        history = body.get("expeditionHistory") if isinstance(body, dict) else None
        if not history:
            return TrackingUpdate(status=None, label="")
        latest = max(history, key=lambda entry: str(entry.get("statusDate", "")))
        label = str(latest.get("statusState") or latest.get("status") or latest.get("statusLabel") or "")
        text = " ".join(str(latest.get(key) or "") for key in ("statusState", "status", "statusLabel"))
        return TrackingUpdate(status=classify_carrier_status(text), label=label[:120])
