from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.fitment.models import FitmentSpec
from apps.vehicles.models import VehicleGeneration, VehicleMake, VehicleModel

# DEMO DATA – approximate values compiled from public spec sheets for the university project.
# Not a guarantee of compatibility. Fields per generation:
# (name, year_from, year_to, pcd, center_bore, et_min, et_max, dia_min, dia_max, w_min, w_max,
#  thread, OEM tire sizes)
VEHICLES = {
    "BMW": {
        "Seria 3": [
            ("F30 / F31", 2012, 2019, "5x120", "72.6", 20, 45, 16, 19, "7.0", "8.5", "M14x1.25",
             ["225/50 R17", "225/45 R18", "225/40 R19"]),
            ("G20 / G21", 2019, None, "5x112", "66.6", 20, 40, 17, 20, "7.5", "9.0", "M14x1.25",
             ["225/50 R17", "225/45 R18", "225/40 R19"]),
        ],
        "Seria 5": [
            ("F10 / F11", 2010, 2017, "5x120", "72.6", 15, 35, 17, 20, "8.0", "9.5", "M14x1.25",
             ["225/55 R17", "245/45 R18", "245/40 R19"]),
            ("G30 / G31", 2017, 2023, "5x112", "66.6", 20, 35, 17, 20, "7.5", "9.0", "M14x1.25",
             ["225/55 R17", "245/45 R18", "245/40 R19"]),
        ],
    },
    "Audi": {
        "A4": [
            ("B8", 2008, 2015, "5x112", "66.6", 30, 45, 16, 19, "7.0", "8.5", "M14x1.5",
             ["225/50 R17", "245/40 R18", "255/35 R19"]),
            ("B9", 2015, 2024, "5x112", "66.5", 25, 45, 17, 20, "7.5", "9.0", "M14x1.5",
             ["225/50 R17", "245/40 R18", "255/35 R19"]),
        ],
        "A5": [
            ("F5", 2016, 2024, "5x112", "66.5", 25, 45, 17, 20, "7.5", "9.0", "M14x1.5",
             ["225/50 R17", "245/40 R18", "255/35 R19"]),
        ],
    },
    "Volkswagen": {
        "Golf": [
            ("VII", 2012, 2020, "5x112", "57.1", 40, 50, 15, 19, "6.0", "8.0", "M14x1.5",
             ["205/55 R16", "225/45 R17", "225/40 R18"]),
            ("VIII", 2020, None, "5x112", "57.1", 40, 50, 16, 19, "6.5", "8.0", "M14x1.5",
             ["205/55 R16", "225/45 R17", "225/40 R18"]),
        ],
        "Passat": [
            ("B8", 2014, 2023, "5x112", "57.1", 35, 45, 16, 19, "6.5", "8.5", "M14x1.5",
             ["215/55 R17", "235/45 R18", "235/40 R19"]),
        ],
    },
    "Mercedes-Benz": {
        "Clasa C": [
            ("W205", 2014, 2021, "5x112", "66.6", 35, 50, 16, 19, "7.0", "8.5", "M14x1.5",
             ["225/50 R17", "225/45 R18", "225/40 R19"]),
            ("W206", 2021, None, "5x112", "66.6", 35, 50, 17, 19, "7.0", "8.5", "M14x1.5",
             ["225/55 R17", "225/45 R18", "225/40 R19"]),
        ],
        "Clasa E": [
            ("W213", 2016, 2023, "5x112", "66.6", 30, 45, 17, 20, "7.5", "9.0", "M14x1.5",
             ["225/55 R17", "245/45 R18", "245/40 R19"]),
        ],
    },
}


class Command(BaseCommand):
    help = "Create/update demo vehicles (makes, models, generations) with fitment specs. Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        generations = 0
        for make_name, models in VEHICLES.items():
            make, _ = VehicleMake.objects.update_or_create(
                slug=slugify(make_name), defaults={"name": make_name}
            )
            for model_name, rows in models.items():
                model, _ = VehicleModel.objects.update_or_create(
                    make=make, slug=slugify(model_name), defaults={"name": model_name}
                )
                for row in rows:
                    (name, y_from, y_to, pcd, bore, et_min, et_max,
                     d_min, d_max, w_min, w_max, thread, tires) = row
                    generation, _ = VehicleGeneration.objects.update_or_create(
                        model=model, name=name, defaults={"year_from": y_from, "year_to": y_to}
                    )
                    FitmentSpec.objects.update_or_create(
                        generation=generation,
                        defaults={
                            "pcd": pcd,
                            "center_bore_mm": Decimal(bore),
                            "et_min": et_min,
                            "et_max": et_max,
                            "diameter_min": d_min,
                            "diameter_max": d_max,
                            "width_min": Decimal(w_min),
                            "width_max": Decimal(w_max),
                            "thread_size": thread,
                            "tire_sizes": tires,
                            "notes": "Demo data – verify before real use.",
                        },
                    )
                    generations += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {generations} vehicle generations."))
