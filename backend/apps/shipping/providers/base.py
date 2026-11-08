"""Shared carrier contract, errors, HTTP helpers and status classification."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings

from apps.orders.models import Order

TIMEOUT_SECONDS = 20


class CarrierError(Exception):
    pass


class CarrierConfigurationError(CarrierError):
    """Missing/invalid settings or credentials; nothing was sent to the carrier."""


class CarrierRejectedError(CarrierError):
    """The carrier refused the request or was unreachable before anything was created."""


class CarrierAmbiguousError(CarrierError):
    """An AWB may or may not exist; staff must check the carrier portal before retrying."""


@dataclass(frozen=True)
class AwbResult:
    awb: str
    tracking_url: str


@dataclass(frozen=True)
class TrackingUpdate:
    status: str | None
    label: str


# Carrier status vocabularies are not published, so classify by keyword (RO + EN).
# Order matters: negative/return phrases are checked before "delivered".
_STATUS_RULES = (
    (re.compile(r"\bretur|\breturn"), "returned"),
    (re.compile(r"nelivrat|not delivered|undelivered|refuz|refused"), None),
    (re.compile(r"\blivrat|\bdelivered"), "delivered"),
    (re.compile(r"tranzit|transit|hub|depozit|curs de livrare|out for delivery|sortat|sorted"), "in_transit"),
    (re.compile(r"ridicat|picked up|preluat"), "picked_up"),
)


def classify_carrier_status(text: str) -> str | None:
    lowered = (text or "").lower()
    for pattern, status in _STATUS_RULES:
        if pattern.search(lowered):
            return status
    return None


def shipping_mode() -> str:
    mode = (settings.SHIPPING_MODE or "").strip().lower()
    if mode not in ("sandbox", "live"):
        raise CarrierConfigurationError("SHIPPING_MODE must be 'sandbox' or 'live'.")
    return mode


def require(*values: str, message: str) -> None:
    if not all(str(value or "").strip() for value in values):
        raise CarrierConfigurationError(message)


def tracking_url(template: str, awb: str) -> str:
    return template.format(awb=awb) if template else ""


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return None


def error_text(body, fallback: str) -> str:
    """Flatten a carrier validation-error body into a short, staff-readable message."""
    messages: list[str] = []

    def walk(node):
        if isinstance(node, str):
            messages.append(node)
        elif isinstance(node, dict):
            for key, value in node.items():
                if key in ("error", "errors", "message") or isinstance(value, (dict, list)):
                    walk(value)
                elif isinstance(value, str):
                    messages.append(f"{key}: {value}")
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(body)
    return ("; ".join(messages) or fallback)[:500]


def ensure_pdf(response, carrier: str) -> bytes:
    content = getattr(response, "content", b"")
    if not 200 <= response.status_code < 300 or not isinstance(content, bytes) or not content.startswith(b"%PDF"):
        raise CarrierRejectedError(f"{carrier} did not return a PDF label.")
    return content


def total_weight(parcels: list[Decimal]) -> Decimal:
    return sum(parcels, Decimal("0")).quantize(Decimal("0.01"))


class CarrierProvider(ABC):
    name: str
    display_name: str

    @abstractmethod
    def create_awb(self, order: Order, *, parcels: list[Decimal]) -> AwbResult: ...

    @abstractmethod
    def download_label(self, awb: str) -> bytes: ...

    @abstractmethod
    def track(self, awb: str) -> TrackingUpdate: ...

    def _login_request(self, send):
        """Run a login call; network failures here are safe to retry (nothing was created)."""
        try:
            response = send()
        except requests.RequestException as exc:
            raise CarrierRejectedError(f"{self.display_name} is unreachable; try again later.") from exc
        if response.status_code in (401, 403):
            raise CarrierConfigurationError(f"{self.display_name} rejected the configured credentials.")
        if not 200 <= response.status_code < 300:
            raise CarrierRejectedError(f"{self.display_name} login failed (HTTP {response.status_code}).")
        return safe_json(response)

    def _read_request(self, send, what: str):
        """GET-style calls (labels, tracking): any failure is retryable."""
        try:
            response = send()
        except requests.RequestException as exc:
            raise CarrierRejectedError(f"{self.display_name} {what} request failed.") from exc
        if not 200 <= response.status_code < 300:
            raise CarrierRejectedError(f"{self.display_name} {what} request failed (HTTP {response.status_code}).")
        return response
