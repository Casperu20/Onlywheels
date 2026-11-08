"""
Courier AWB lifecycle (Sameday / FAN Courier).

1. Staff moves a courier order to "processing" → `queue_shipment` creates a pending `Shipment`
   and `create_shipment_task` runs after commit: parcels come from the snapshotted item weights,
   the carrier creates the AWB, the order moves to "shipped" and the label is stored privately.
2. Celery Beat runs `refresh_shipments_task` hourly; carrier statuses only move forward and
   "delivered" completes the courier order.
3. The customer sees the AWB and tracking link on the order page.

Rejected requests mark the shipment failed (safe to retry). Unclear outcomes (timeouts, 5xx)
need review: staff check the carrier portal for the order number before retrying.
"""

from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.catalog.models import ProductType
from apps.orders.models import Order

from .models import Shipment
from .providers import (
    CarrierAmbiguousError,
    CarrierConfigurationError,
    CarrierError,
    CarrierRejectedError,
    get_carrier_provider,
)

Status = Shipment.Status
OPEN_STATUSES = (Status.CREATED, Status.PICKED_UP, Status.IN_TRANSIT)
_RANK = {Status.CREATED: 1, Status.PICKED_UP: 2, Status.IN_TRANSIT: 3, Status.DELIVERED: 4, Status.RETURNED: 4}


class ShipmentDataError(Exception):
    """The order cannot be shipped until staff fixes its data (e.g. missing weights)."""


class ShipmentStateError(Exception):
    """The requested action is not allowed in the shipment's current state."""


def parcel_weights(order: Order) -> list[Decimal]:
    """One parcel per wheel/tire/set unit; all accessories travel together in one parcel."""
    parcels: list[Decimal] = []
    accessories = Decimal("0")
    for item in order.items.all():
        if item.shipping_weight_kg is None or item.shipping_weight_kg <= 0:
            raise ShipmentDataError(f"Item {item.sku} has no shipping weight; set it on the variant and order item.")
        if item.product_type == ProductType.ACCESSORY:
            accessories += item.shipping_weight_kg * item.quantity
        else:
            parcels.extend([item.shipping_weight_kg] * item.quantity)
    if accessories:
        parcels.append(accessories)
    if not parcels:
        raise ShipmentDataError("The order has no items to ship.")
    return parcels


def _save(shipment: Shipment, **fields) -> Shipment:
    for name, value in fields.items():
        setattr(shipment, name, value)
    shipment.save(update_fields=[*fields, "updated_at"])
    return shipment


def _fail(shipment: Shipment, status: str, message: str) -> Shipment:
    return _save(shipment, status=status, last_error=str(message)[:1000])


def queue_shipment(order: Order) -> Shipment | None:
    """Called inside the staff "processing" transition. Courier orders only; no-op when disabled."""
    if order.delivery_method != Order.Delivery.COURIER or not settings.SHIPPING_CARRIER:
        return None
    from .tasks import create_shipment_task

    shipment, _ = Shipment.objects.get_or_create(order=order, defaults={"carrier": settings.SHIPPING_CARRIER})
    transaction.on_commit(lambda: create_shipment_task.delay(str(order.pk)), robust=True)
    return shipment


def create_shipment(order: Order) -> Shipment:
    """Create the AWB once. Safe to call repeatedly: only pending/failed shipments are attempted."""
    with transaction.atomic():
        shipment, _ = Shipment.objects.get_or_create(
            order=order, defaults={"carrier": settings.SHIPPING_CARRIER or Shipment.Carrier.SAMEDAY}
        )
        shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
        order = Order.objects.get(pk=order.pk)
        if shipment.status not in (Status.PENDING, Status.FAILED):
            return shipment
        if order.status != Order.Status.PROCESSING:
            return _fail(shipment, Status.FAILED, f"Order is {order.get_status_display()}, not processing.")
        try:
            parcels = parcel_weights(order)
            provider = get_carrier_provider()
        except (ShipmentDataError, CarrierConfigurationError) as exc:
            return _fail(shipment, Status.FAILED, str(exc))
        _save(
            shipment,
            carrier=provider.name,
            status=Status.CREATING,
            attempt_count=shipment.attempt_count + 1,
            last_attempted_at=timezone.now(),
            last_error="",
            parcels=len(parcels),
            weight_kg=sum(parcels, Decimal("0")),
        )

    try:
        result = provider.create_awb(order, parcels=parcels)
    except (CarrierConfigurationError, CarrierRejectedError) as exc:
        return _fail(shipment, Status.FAILED, str(exc))
    except CarrierAmbiguousError as exc:
        return _fail(shipment, Status.REVIEW_REQUIRED, str(exc))

    _save(shipment, awb=result.awb, tracking_url=result.tracking_url, status=Status.CREATED)
    _mark_order_shipped(shipment, provider.display_name)
    fetch_label(shipment, provider=provider)
    return shipment


def _mark_order_shipped(shipment: Shipment, carrier_name: str) -> None:
    from apps.orders.services import change_status

    try:
        change_status(shipment.order, Order.Status.SHIPPED, note=f"{carrier_name} AWB {shipment.awb}")
    except ValidationError:
        _save(shipment, last_error="AWB created but the order could not be marked shipped; check its status.")


def fetch_label(shipment: Shipment, *, provider=None) -> Shipment:
    if not shipment.awb:
        raise ShipmentStateError("The shipment has no AWB yet.")
    try:
        provider = provider or get_carrier_provider(shipment.carrier)
        pdf = provider.download_label(shipment.awb)
    except CarrierError as exc:
        return _save(shipment, last_error=f"Label download failed: {exc}"[:1000])
    shipment.label_pdf.save(f"{slugify(shipment.awb) or 'awb'}.pdf", ContentFile(pdf), save=False)
    return _save(shipment, label_pdf=shipment.label_pdf, last_error="")


def retry_shipment(shipment: Shipment, *, confirmed_absent: bool = False) -> Shipment:
    """Retry a failed AWB. Review/creating states need staff to confirm no AWB exists at the carrier."""
    shipment.refresh_from_db()
    if shipment.status in (Status.REVIEW_REQUIRED, Status.CREATING):
        if not confirmed_absent:
            raise ShipmentStateError("Confirm in the carrier portal that no AWB exists before retrying.")
        _save(shipment, status=Status.FAILED)
    elif shipment.status != Status.FAILED:
        raise ShipmentStateError(f"A {shipment.get_status_display().lower()} shipment cannot be retried.")
    return create_shipment(shipment.order)


def adopt_manual_awb(shipment: Shipment) -> Shipment:
    """Staff found the AWB in the carrier portal and typed it in: track it and ship the order."""
    shipment.refresh_from_db()
    awb = shipment.awb.strip()
    if not awb:
        raise ShipmentStateError("Type the AWB from the carrier portal into the shipment first.")
    if shipment.status not in (Status.REVIEW_REQUIRED, Status.FAILED, Status.CREATING, Status.PENDING):
        raise ShipmentStateError(f"A {shipment.get_status_display().lower()} shipment already has its AWB.")
    templates = {
        Shipment.Carrier.SAMEDAY: settings.SAMEDAY_TRACKING_URL,
        Shipment.Carrier.FAN_COURIER: settings.FAN_COURIER_TRACKING_URL,
    }
    template = templates.get(shipment.carrier, "")
    _save(
        shipment,
        awb=awb,
        tracking_url=template.format(awb=awb) if template else "",
        status=Status.CREATED,
        last_error="",
    )
    _mark_order_shipped(shipment, shipment.get_carrier_display())
    return shipment


def refresh_tracking(shipment: Shipment) -> Shipment:
    try:
        update = get_carrier_provider(shipment.carrier).track(shipment.awb)
    except CarrierError as exc:
        return _save(shipment, last_error=str(exc)[:1000], last_tracked_at=timezone.now())

    fields = {"last_tracked_at": timezone.now(), "last_error": ""}
    if update.label:
        fields["carrier_status"] = update.label
    current, new = shipment.status, update.status
    if new in _RANK and current in OPEN_STATUSES and _RANK[new] > _RANK[current]:
        fields["status"] = new
    _save(shipment, **fields)

    order = shipment.order
    if (
        shipment.status == Status.DELIVERED
        and order.delivery_method == Order.Delivery.COURIER
        and order.status == Order.Status.SHIPPED
    ):
        from apps.orders.services import change_status

        change_status(order, Order.Status.COMPLETED, note=f"Delivered (AWB {shipment.awb})")
    return shipment


def refresh_shipments() -> int:
    count = 0
    for shipment in Shipment.objects.filter(status__in=OPEN_STATUSES).exclude(awb="").select_related("order"):
        refresh_tracking(shipment)
        count += 1
    return count
