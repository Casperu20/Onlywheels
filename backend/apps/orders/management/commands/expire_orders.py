from django.core.management.base import BaseCommand

from apps.orders.services import expire_unpaid_orders


class Command(BaseCommand):
    help = "Cancel unpaid orders whose reservation expired (Celery Beat does this every 5 min)."

    def handle(self, *args, **options):
        count = expire_unpaid_orders()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} unpaid order(s)."))
