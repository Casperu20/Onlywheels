from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.appointments.models import Appointment
from apps.orders.models import Order


def _send(template: str, subject: str, context: dict, recipients: list[str]) -> None:
    recipients = [r for r in recipients if r]
    if not recipients:
        return
    send_mail(
        subject=subject,
        message=render_to_string(f"emails/{template}.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
    )


def _load(order_id: str) -> Order | None:
    return (
        Order.objects.select_related("appointment__garage")
        .prefetch_related("items", "appointment__garage__partner_users")
        .filter(pk=order_id)
        .first()
    )


def _appointment(order: Order) -> Appointment | None:
    try:
        return order.appointment
    except Appointment.DoesNotExist:
        return None


def _context(order: Order) -> dict:
    return {
        "order": order,
        "items": list(order.items.all()),
        "appointment": _appointment(order),
        "order_url": f"{settings.FRONTEND_URL}/account/orders/{order.number}",
    }


@shared_task
def send_order_confirmation(order_id: str) -> None:
    order = _load(order_id)
    if order is None:
        return
    context = _context(order)
    _send(
        "order_confirmation",
        f"OnlyWheels – comanda {order.number} a fost plătită / order paid",
        context,
        [order.email],
    )

    appointment = context["appointment"]
    if appointment is not None:
        garage = appointment.garage
        partner_emails = [u.email for u in garage.partner_users.all()]
        _send(
            "garage_booking",
            f"OnlyWheels – programare nouă {appointment.slot_start:%d.%m.%Y %H:%M} ({order.number})",
            context,
            [garage.email, *partner_emails],
        )


@shared_task
def send_order_status_update(order_id: str) -> None:
    order = _load(order_id)
    if order is None:
        return
    _send(
        "order_status",
        f"OnlyWheels – comanda {order.number}: {order.get_status_display()}",
        _context(order),
        [order.email],
    )
