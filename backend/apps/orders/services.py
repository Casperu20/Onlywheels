"""
Order lifecycle:

    cart ──place_order──▶ pending_payment (stock reserved, garage slot held, cart emptied)
         ├─ mark_paid ──▶ paid (stock deducted, slot booked, voucher used, confirmation email)
         └─ expire / cancel ──▶ cancelled (reservation + slot released)
    paid ─▶ processing ─▶ shipped | ready_for_fitting ─▶ completed   (staff, via admin)
"""

import secrets
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.appointments.models import Appointment
from apps.appointments.services import hold_slot
from apps.cart import services as cart_services
from apps.cart.models import CartItem
from apps.garages.models import Garage
from apps.inventory.models import StockItem
from apps.pricing.models import Voucher
from apps.pricing.services import discount_for, get_valid_voucher, register_use

from .models import Order, OrderItem, OrderStatusChange

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
Status = Order.Status

STAFF_TRANSITIONS = {
    Status.PAID: {Status.PROCESSING, Status.CANCELLED},
    Status.PROCESSING: {Status.SHIPPED, Status.READY_FOR_FITTING, Status.CANCELLED},
    Status.SHIPPED: {Status.COMPLETED},
    Status.READY_FOR_FITTING: {Status.COMPLETED},
}


class OutOfStock(APIException):
    status_code = 409
    default_code = "out_of_stock"
    default_detail = "Some products are no longer available in the requested quantity."


@dataclass(frozen=True)
class Quote:
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    fitting: Decimal
    total: Decimal
    vat: Decimal
    voucher: Voucher | None

    @property
    def voucher_code(self) -> str | None:
        return self.voucher.code if self.voucher else None


def vat_included(total: Decimal) -> Decimal:
    return (total - total / (1 + settings.VAT_RATE)).quantize(CENT, rounding=ROUND_HALF_UP)


def build_quote(
    items: list[CartItem],
    *,
    delivery_method: str,
    garage: Garage | None = None,
    voucher_code: str = "",
) -> Quote:
    if not items:
        raise ValidationError({"non_field_errors": ["Your cart is empty."]})

    subtotal = cart_services.subtotal(items)
    voucher = get_valid_voucher(voucher_code, subtotal) if voucher_code.strip() else None
    discount = discount_for(voucher, subtotal) if voucher else ZERO

    if delivery_method == Order.Delivery.GARAGE_FITTING:
        # Products are delivered to the partner garage at no extra cost; fitting is charged.
        shipping = ZERO
        fitting = garage.fitting_price if garage else ZERO
    else:
        free = subtotal - discount >= settings.FREE_SHIPPING_THRESHOLD
        shipping = ZERO if free else settings.SHIPPING_FLAT_RATE
        fitting = ZERO

    total = subtotal - discount + shipping + fitting
    return Quote(subtotal, discount, shipping, fitting, total, vat_included(total), voucher)


def _new_number() -> str:
    while True:
        number = f"OW{timezone.localdate():%y%m%d}-{secrets.token_hex(3).upper()}"
        if not Order.objects.filter(number=number).exists():
            return number


def add_history(order: Order, status: str, note: str = "", by=None) -> None:
    OrderStatusChange.objects.create(order=order, status=status, note=note[:255], changed_by=by)


def _locked_stock(variant_ids) -> dict:
    rows = StockItem.objects.select_for_update().filter(variant_id__in=variant_ids).order_by("variant_id")
    return {row.variant_id: row for row in rows}


def _notify(task_name: str, order: Order) -> None:
    from apps.notifications import tasks

    order_id = str(order.pk)
    transaction.on_commit(lambda: getattr(tasks, task_name).delay(order_id))


def place_order(user, data: dict) -> Order:
    """Create an order from the user's cart. `data` comes from CheckoutSerializer."""
    expire_unpaid_orders()
    return _place_order(user, data)


@transaction.atomic
def _place_order(user, data: dict) -> Order:
    cart = cart_services.get_cart(user)
    items = list(cart_services.cart_items(cart).order_by("variant_id"))
    delivery = data["delivery_method"]
    garage = data.get("garage") if delivery == Order.Delivery.GARAGE_FITTING else None
    quote = build_quote(
        items, delivery_method=delivery, garage=garage, voucher_code=data.get("voucher_code", "")
    )

    stock = _locked_stock([item.variant_id for item in items])
    missing = [
        item.variant.sku
        for item in items
        if item.variant_id not in stock or stock[item.variant_id].available < item.quantity
    ]
    if missing:
        raise OutOfStock(f"Not enough stock for: {', '.join(missing)}")

    order = Order.objects.create(
        number=_new_number(),
        user=user,
        delivery_method=delivery,
        email=data["email"],
        full_name=data["full_name"],
        phone=data["phone"],
        line1=data["line1"],
        line2=data.get("line2", ""),
        city=data["city"],
        county=data["county"],
        postal_code=data["postal_code"],
        notes=data.get("notes", ""),
        subtotal=quote.subtotal,
        discount=quote.discount,
        shipping=quote.shipping,
        fitting=quote.fitting,
        total=quote.total,
        vat=quote.vat,
        voucher=quote.voucher,
        voucher_code=quote.voucher_code or "",
        reserved_until=timezone.now() + timedelta(minutes=settings.ORDER_RESERVATION_MINUTES),
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                variant=item.variant,
                product_name=str(item.variant.product),
                product_slug=item.variant.product.slug,
                product_type=item.variant.product.type,
                sku=item.variant.sku,
                description=item.variant.summary()[:255],
                unit_price=item.variant.price,
                quantity=item.quantity,
                line_total=item.variant.price * item.quantity,
            )
            for item in items
        ]
    )
    for item in items:
        row = stock[item.variant_id]
        row.reserved += item.quantity
        row.save(update_fields=["reserved", "updated_at"])

    if garage is not None:
        hold_slot(garage, data["slot_start"], order)

    add_history(order, Status.PENDING_PAYMENT, "Order placed", by=user)
    cart_services.clear(cart)
    return order


@transaction.atomic
def mark_paid(order: Order, *, note: str = "Payment received") -> Order:
    """Idempotent: safe to call again for the same order (e.g. repeated webhooks)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.paid_at is not None:
        return order

    was_cancelled = order.status == Status.CANCELLED
    items = list(order.items.all())
    stock = _locked_stock([item.variant_id for item in items if item.variant_id])
    for item in items:
        row = stock.get(item.variant_id)
        if row is None:
            continue
        if not was_cancelled:
            row.reserved = max(row.reserved - item.quantity, 0)
        row.quantity = max(row.quantity - item.quantity, 0)
        row.reserved = min(row.reserved, row.quantity)
        row.save(update_fields=["quantity", "reserved", "updated_at"])

    order.status = Status.PAID
    order.paid_at = timezone.now()
    order.reserved_until = None
    order.save(update_fields=["status", "paid_at", "reserved_until", "updated_at"])

    Appointment.objects.filter(
        order=order, status__in=(Appointment.Status.HELD, Appointment.Status.CANCELLED)
    ).update(status=Appointment.Status.BOOKED)
    if order.voucher_id:
        register_use(order.voucher)

    if was_cancelled:
        note = "Payment received after the reservation expired – check stock and fitting slot."
    add_history(order, Status.PAID, note)
    _notify("send_order_confirmation", order)
    return order


@transaction.atomic
def cancel_order(order: Order, *, note: str, by=None) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == Status.CANCELLED:
        return order
    if order.status not in (Status.PENDING_PAYMENT, Status.PAID, Status.PROCESSING):
        raise ValidationError({"non_field_errors": ["This order can no longer be cancelled."]})

    was_paid = order.status != Status.PENDING_PAYMENT
    items = list(order.items.all())
    stock = _locked_stock([item.variant_id for item in items if item.variant_id])
    for item in items:
        row = stock.get(item.variant_id)
        if row is None:
            continue
        if was_paid:
            row.quantity += item.quantity  # back on the shelf; refund is handled manually
        else:
            row.reserved = max(row.reserved - item.quantity, 0)
        row.save(update_fields=["quantity", "reserved", "updated_at"])

    Appointment.objects.filter(order=order).exclude(status=Appointment.Status.COMPLETED).update(
        status=Appointment.Status.CANCELLED
    )
    order.status = Status.CANCELLED
    order.reserved_until = None
    order.save(update_fields=["status", "reserved_until", "updated_at"])
    add_history(order, Status.CANCELLED, note, by=by)
    if was_paid:
        _notify("send_order_status_update", order)
    return order


def expire_unpaid_orders(now=None) -> int:
    now = now or timezone.now()
    expired = Order.objects.filter(
        status=Status.PENDING_PAYMENT, reserved_until__lt=now
    ).values_list("pk", flat=True)
    count = 0
    for pk in list(expired):
        cancel_order(Order(pk=pk), note="Payment not received in time – reservation expired.")
        count += 1
    return count


@transaction.atomic
def change_status(order: Order, new_status: str, *, by=None, note: str = "") -> Order:
    """Staff transitions after payment (admin actions)."""
    if new_status == Status.CANCELLED:
        return cancel_order(order, note=note or "Cancelled by staff", by=by)

    order = Order.objects.select_for_update().get(pk=order.pk)
    if new_status not in STAFF_TRANSITIONS.get(order.status, set()):
        raise ValidationError(
            {"status": [f"Cannot change status from {order.status} to {new_status}."]}
        )
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    if new_status == Status.COMPLETED:
        Appointment.objects.filter(
            order=order, status__in=(Appointment.Status.BOOKED, Appointment.Status.CONFIRMED)
        ).update(status=Appointment.Status.COMPLETED)
    add_history(order, new_status, note, by=by)
    _notify("send_order_status_update", order)
    return order
