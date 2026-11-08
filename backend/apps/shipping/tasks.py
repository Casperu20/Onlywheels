from celery import shared_task

from apps.orders.models import Order

from .services import create_shipment, refresh_shipments


@shared_task
def create_shipment_task(order_id: str) -> str:
    return create_shipment(Order.objects.get(pk=order_id)).status


@shared_task
def refresh_shipments_task() -> int:
    return refresh_shipments()
