from celery import shared_task

from apps.invoicing.services import issue_invoice
from apps.orders.models import Order


@shared_task
def issue_invoice_task(order_id: str) -> str:
    order = Order.objects.get(pk=order_id)
    invoice = issue_invoice(order)
    return str(invoice.pk)
