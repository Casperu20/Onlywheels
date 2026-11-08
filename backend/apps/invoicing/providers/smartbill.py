from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.utils import timezone

from apps.orders.models import Order


class SmartBillError(Exception):
    pass


class SmartBillConfigurationError(SmartBillError):
    pass


class SmartBillRejectedError(SmartBillError):
    pass


class SmartBillAmbiguousError(SmartBillError):
    pass


class SmartBillPDFError(SmartBillError):
    pass


@dataclass(frozen=True)
class SmartBillInvoiceResult:
    series: str
    number: str
    document_id: str
    issued_at: datetime
    total: Decimal
    efactura_status: str | None = None


class SmartBillProvider:
    timeout = 15

    def _configuration(self) -> tuple[str, tuple[str, str]]:
        if not settings.SMARTBILL_ENABLED:
            raise SmartBillConfigurationError("SmartBill invoicing is disabled.")

        base_url = settings.SMARTBILL_API_BASE_URL.strip().rstrip("/")
        try:
            parsed_url = urlsplit(base_url)
        except ValueError as exc:
            raise SmartBillConfigurationError("SmartBill API URL must be an absolute HTTPS URL.") from exc
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise SmartBillConfigurationError("SmartBill API URL must be an absolute HTTPS URL.")

        user = settings.SMARTBILL_USER.strip()
        token = settings.SMARTBILL_TOKEN.strip()
        required = (
            settings.SMARTBILL_CIF.strip(),
            settings.SMARTBILL_SERIES.strip(),
            settings.SMARTBILL_TAX_NAME.strip(),
            settings.SMARTBILL_MEASURING_UNIT.strip(),
        )
        if not user or not token or not all(required):
            raise SmartBillConfigurationError(
                "SmartBill account, company, series, tax, and unit settings are required."
            )
        return base_url, (user, token)

    def _tax_fields(self) -> dict:
        return {
            "measuringUnitName": settings.SMARTBILL_MEASURING_UNIT,
            "taxName": settings.SMARTBILL_TAX_NAME,
            "taxPercentage": float(Decimal(str(settings.VAT_RATE)) * 100),
            "isTaxIncluded": True,
        }

    def _products(self, order: Order) -> list[dict]:
        items = list(order.items.order_by("created_at"))
        if not items:
            raise SmartBillConfigurationError("An order must contain at least one product to invoice.")

        product_lines = []
        subtotal = Decimal("0.00")
        for item in items:
            if item.quantity <= 0 or item.unit_price < 0:
                raise SmartBillConfigurationError("Order items contain an invalid quantity or price.")
            subtotal += item.line_total
            product_lines.append(
                {
                    "name": item.product_name,
                    "code": item.sku,
                    "quantity": item.quantity,
                    "price": float(item.unit_price),
                    **self._tax_fields(),
                }
            )
        if subtotal != order.subtotal:
            raise SmartBillConfigurationError("Order items do not match the stored order subtotal.")

        lines = product_lines
        if order.discount:
            if order.discount < 0:
                raise SmartBillConfigurationError("Order discount cannot be negative.")
            lines = [
                *lines,
                {
                    "name": "Order discount",
                    "quantity": 1,
                    "price": 0.0,
                    **self._tax_fields(),
                    "isDiscount": True,
                    "discountType": 1,
                    "discountValue": -float(order.discount),
                    "numberOfItems": len(product_lines),
                },
            ]

        for label, amount in (("Shipping", order.shipping), ("Fitting", order.fitting)):
            if amount < 0:
                raise SmartBillConfigurationError(f"{label} amount cannot be negative.")
            if amount:
                lines.append(
                    {
                        "name": label,
                        "quantity": 1,
                        "price": float(amount),
                        **self._tax_fields(),
                        "isService": True,
                    }
                )

        if order.total != order.subtotal - order.discount + order.shipping + order.fitting:
            raise SmartBillConfigurationError("Invoice lines do not match the stored order total.")
        return lines

    @staticmethod
    def _error_message(body) -> str:
        if isinstance(body, dict):
            error_text = body.get("errorText")
            if isinstance(error_text, str) and error_text.strip():
                return error_text.strip()[:500]
            errors = body.get("errors")
            if isinstance(errors, list) and errors and isinstance(errors[0], dict):
                parameter = errors[0].get("param")
                if isinstance(parameter, str) and parameter:
                    return f"SmartBill rejected the invoice request field: {parameter[:100]}."
        return "SmartBill rejected the invoice request."

    def issue(self, order: Order, *, reference: str) -> SmartBillInvoiceResult:
        base_url, auth = self._configuration()
        if order.currency != "RON":
            raise SmartBillConfigurationError("SmartBill invoicing currently supports RON orders only.")

        address = " ".join(part for part in (order.line1, order.line2) if part)
        payload = {
            "companyVatCode": settings.SMARTBILL_CIF.strip(),
            "seriesName": settings.SMARTBILL_SERIES.strip(),
            "issueDate": timezone.localdate().isoformat(),
            "observations": f"OnlyWheels order {reference}",
            "client": {
                "name": order.full_name,
                "country": order.country,
                "address": address,
                "city": order.city,
                "county": order.county,
                "email": order.email,
                "phone": order.phone,
            },
            "products": self._products(order),
        }
        try:
            response = requests.post(
                f"{base_url}/invoice/v2",
                json=payload,
                auth=auth,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SmartBillAmbiguousError(
                "SmartBill invoice creation outcome is unknown; reconcile the order in SmartBill before retrying."
            ) from exc

        status_code = response.status_code
        try:
            body = response.json()
        except ValueError as exc:
            if status_code >= 500 or 200 <= status_code < 300:
                raise SmartBillAmbiguousError(
                    "SmartBill returned an unreadable invoice response; reconcile before retrying."
                ) from exc
            raise SmartBillRejectedError("SmartBill rejected the invoice request.") from exc

        if 400 <= status_code < 500:
            raise SmartBillRejectedError(self._error_message(body))
        if status_code >= 500 or not 200 <= status_code < 300:
            raise SmartBillAmbiguousError("SmartBill returned an HTTP error; reconcile the order before retrying.")
        if not isinstance(body, dict):
            raise SmartBillAmbiguousError("SmartBill returned an invalid invoice response; reconcile before retrying.")
        if body.get("errorText") not in ("", None):
            raise SmartBillRejectedError(self._error_message(body))
        if body.get("errorText") != "":
            raise SmartBillAmbiguousError(
                "SmartBill returned an incomplete invoice response; reconcile before retrying."
            )

        series = body.get("series")
        number = body.get("number")
        document_id = body.get("documentId")
        if (
            not isinstance(series, str)
            or not series.strip()
            or not isinstance(number, str)
            or not number.strip()
            or isinstance(document_id, bool)
            or not isinstance(document_id, int)
            or document_id <= 0
        ):
            raise SmartBillAmbiguousError("SmartBill returned incomplete invoice metadata; reconcile before retrying.")
        return SmartBillInvoiceResult(
            series=series.strip(),
            number=number.strip(),
            document_id=str(document_id),
            issued_at=timezone.now(),
            total=order.total,
        )

    def download_pdf(self, *, series: str, number: str) -> bytes:
        base_url, auth = self._configuration()
        try:
            response = requests.get(
                f"{base_url}/invoice/pdf",
                params={
                    "cif": settings.SMARTBILL_CIF.strip(),
                    "seriesname": series,
                    "number": number,
                },
                headers={"Accept": "application/octet-stream"},
                auth=auth,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SmartBillPDFError("SmartBill invoice PDF could not be downloaded.") from exc
        if not 200 <= response.status_code < 300:
            raise SmartBillPDFError("SmartBill invoice PDF could not be downloaded.")
        content = response.content
        if not isinstance(content, bytes) or not content.startswith(b"%PDF-"):
            raise SmartBillPDFError("SmartBill returned an invalid invoice PDF.")
        return content
