from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.pricing.models import Voucher

VOUCHERS = [
    ("BINEAIVENIT10", Voucher.Kind.PERCENT, Decimal("10"), Decimal("500"), "10% la prima comandă (demo)"),
    ("ROTI100", Voucher.Kind.FIXED, Decimal("100"), Decimal("2000"), "100 RON reducere peste 2000 RON (demo)"),
]


class Command(BaseCommand):
    help = "Create demo voucher codes. Idempotent."

    def handle(self, *args, **options):
        for code, kind, value, min_total, description in VOUCHERS:
            Voucher.objects.update_or_create(
                code=code,
                defaults={
                    "kind": kind,
                    "value": value,
                    "min_order_total": min_total,
                    "description": description,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded vouchers: {', '.join(v[0] for v in VOUCHERS)}"))
