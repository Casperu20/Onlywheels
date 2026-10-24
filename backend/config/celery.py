import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("onlywheels")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Periodic jobs (Celery Beat). In eager/dev mode run `manage.py expire_orders` instead.
app.conf.beat_schedule = {
    "expire-unpaid-orders": {
        "task": "apps.orders.tasks.expire_unpaid_orders_task",
        "schedule": 300.0,
    },
}
