from celery import shared_task

from .services import expire_unpaid_orders


@shared_task
def expire_unpaid_orders_task() -> int:
    return expire_unpaid_orders()
