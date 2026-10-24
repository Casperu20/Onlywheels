from datetime import time
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.garages.models import Garage

# DEMO DATA – fictional partner garages.
GARAGES = [
    {
        "slug": "auto-expert-cluj",
        "name": "Auto Expert Service",
        "city": "Cluj-Napoca",
        "county": "Cluj",
        "address": "Str. Fabricii 12",
        "phone": "0740 000 101",
        "latitude": Decimal("46.776000"),
        "longitude": Decimal("23.622000"),
        "fitting_price": Decimal("150.00"),
    },
    {
        "slug": "roti-rapide-bucuresti",
        "name": "Roți Rapide",
        "city": "București",
        "county": "București",
        "address": "Bd. Timișoara 45",
        "phone": "0740 000 102",
        "latitude": Decimal("44.425000"),
        "longitude": Decimal("26.032000"),
        "fitting_price": Decimal("180.00"),
        "capacity_per_slot": 3,
    },
    {
        "slug": "vulcanizare-pro-iasi",
        "name": "Vulcanizare Pro",
        "city": "Iași",
        "county": "Iași",
        "address": "Șos. Păcurari 88",
        "phone": "0740 000 103",
        "latitude": Decimal("47.172000"),
        "longitude": Decimal("27.556000"),
        "fitting_price": Decimal("140.00"),
        "closes_at": time(17, 0),
    },
    {
        "slug": "tyre-center-timisoara",
        "name": "Tyre Center",
        "city": "Timișoara",
        "county": "Timiș",
        "address": "Calea Aradului 20",
        "phone": "0740 000 104",
        "latitude": Decimal("45.770000"),
        "longitude": Decimal("21.228000"),
        "fitting_price": Decimal("160.00"),
        "working_days": [0, 1, 2, 3, 4],
    },
]

PARTNER_PERMISSIONS = ("view_appointment", "change_appointment")


class Command(BaseCommand):
    help = "Create demo partner garages and the `garage_partner` group. Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        for data in GARAGES:
            fields = dict(data)
            slug = fields.pop("slug")
            Garage.objects.update_or_create(
                slug=slug,
                defaults={
                    **fields,
                    "email": f"{slug}@garages.onlywheels.local",
                    "description": "Service partener (date demo).",
                },
            )

        group, _ = Group.objects.get_or_create(name="garage_partner")
        group.permissions.set(
            Permission.objects.filter(
                content_type__app_label="appointments", codename__in=PARTNER_PERMISSIONS
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(GARAGES)} garages. Make a partner: staff user + group "
                "'garage_partner' + add the user to Garage.partner_users."
            )
        )
