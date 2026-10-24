import pytest
from django.core.management import call_command

from apps.catalog.models import Product, ProductVariant
from apps.fitment import services
from apps.fitment.models import FitmentSpec
from apps.vehicles.models import VehicleGeneration

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded():
    call_command("seed_demo", verbosity=0)


def test_seed_is_idempotent(seeded):
    counts = (VehicleGeneration.objects.count(), Product.objects.count(), ProductVariant.objects.count())
    call_command("seed_demo", verbosity=0)
    assert counts == (
        VehicleGeneration.objects.count(),
        Product.objects.count(),
        ProductVariant.objects.count(),
    )
    assert counts[0] == FitmentSpec.objects.count() >= 10


def test_every_seeded_car_has_compatible_wheels(seeded, api_client):
    for generation in VehicleGeneration.objects.all():
        response = api_client.get(
            "/api/v1/catalog/products/", {"vehicle": str(generation.pk), "type": "wheel"}
        )
        assert response.json()["count"] > 0, f"No wheels for {generation}"


def test_seed_data_engine_consistency(seeded):
    variants = ProductVariant.objects.select_related("product")
    for spec in FitmentSpec.objects.all():
        expected = {v.pk for v in variants if services.check_variant(spec, v).fits}
        actual = set(
            variants.filter(services.compatible_variants_q(spec)).values_list("pk", flat=True)
        )
        assert actual == expected, spec
