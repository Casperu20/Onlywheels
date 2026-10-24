from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load all demo data (vehicles, catalog + stock, garages, vouchers). Safe to run repeatedly."

    def handle(self, *args, **options):
        call_command("seed_vehicles", stdout=self.stdout)
        call_command("seed_catalog", stdout=self.stdout)
        call_command("seed_garages", stdout=self.stdout)
        call_command("seed_vouchers", stdout=self.stdout)
