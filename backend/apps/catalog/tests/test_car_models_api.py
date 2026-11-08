from decimal import Decimal

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.catalog.models import CarModel3D
from tests.factories import make_generation

pytestmark = pytest.mark.django_db
CAR_MODELS_URL = "/api/v1/catalog/car-models/"


ANCHORS = {
    "axis": "x",
    "wheels": [
        {"x": -1.0, "y": 0.3, "z": -0.7},
        {"x": 1.0, "y": 0.3, "z": -0.7},
        {"x": -1.0, "y": 0.3, "z": 0.7},
        {"x": 1.0, "y": 0.3, "z": 0.7},
    ],
}


def make_car(**overrides) -> CarModel3D:
    fields = {
        "name": "Generic hatchback",
        "slug": "generic-hatchback",
        "body_type": "hatchback",
        "glb_file": SimpleUploadedFile("car.glb", b"glTF"),
        "length_m": Decimal("4.2"),
        "attribution": "Car model by Example, CC BY 4.0",
    }
    return CarModel3D(**{**fields, **overrides})


def test_car_model_accepts_required_metadata_and_defaults_to_glb_front():
    car = make_car()

    car.full_clean()

    assert car.front == "+z"
    assert car.effective_wheel_anchors is None
    assert car.is_usable is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("body_type", "truck"),
        ("front", "north"),
        ("length_m", 0),
        ("attribution", ""),
    ],
)
def test_car_model_rejects_invalid_required_metadata(field, value):
    with pytest.raises(ValidationError):
        make_car(**{field: value}).full_clean()


@pytest.mark.parametrize(
    "anchors",
    [
        {"axis": "x", "wheels": []},
        {"axis": "y", "wheels": ANCHORS["wheels"]},
        {
            "axis": "x",
            "wheels": [
                {"x": 0, "y": 0, "z": float("inf")},
                *ANCHORS["wheels"][1:],
            ],
        },
    ],
)
def test_car_model_rejects_invalid_manual_anchors(anchors):
    with pytest.raises(ValidationError):
        make_car(wheel_anchors=anchors).full_clean()


def test_manual_anchors_override_detection_and_make_car_usable():
    car = make_car(
        wheel_anchors=ANCHORS,
        detected_anchors=None,
        detection_status=CarModel3D.DetectionStatus.FAILED,
        detection_message="Could not find four wheels.",
    )

    car.full_clean()

    assert car.is_usable is True
    assert car.effective_wheel_anchors == ANCHORS


def test_successful_detection_makes_car_usable_without_manual_override():
    car = make_car(
        detected_anchors=ANCHORS,
        detection_status=CarModel3D.DetectionStatus.OK,
    )

    assert car.is_usable is True
    assert car.effective_wheel_anchors == ANCHORS


def test_car_model_admin_registers_editable_catalog_entry_and_only_previews_usable_active_cars(settings):
    settings.FRONTEND_URL = "https://shop.example/"
    model_admin = admin.site._registry.get(CarModel3D)
    assert model_admin is not None
    assert "vehicle_model" in model_admin.autocomplete_fields

    active = make_car(wheel_anchors=ANCHORS, is_active=True)
    assert 'href="https://shop.example/showroom?view=car&amp;car=generic-hatchback"' in str(
        model_admin.preview_link(active)
    )

    inactive = make_car(wheel_anchors=ANCHORS, is_active=False)
    assert "Available after activation" in model_admin.preview_link(inactive)


def create_car_model(**overrides) -> CarModel3D:
    fields = {
        "name": "Generic sedan",
        "slug": "generic-sedan",
        "body_type": "sedan",
        "glb_file": SimpleUploadedFile("car.glb", b"glTF"),
        "length_m": Decimal("4.2"),
        "attribution": "Car model by Example, CC BY 4.0",
        "is_active": True,
        "detected_anchors": ANCHORS,
        "detection_status": CarModel3D.DetectionStatus.OK,
    }
    return CarModel3D.objects.create(**{**fields, **overrides})


def test_car_models_endpoint_is_public_and_returns_sorted_active_usable_models(api_client):
    later = create_car_model(name="Later", slug="later", sort_order=2)
    first = create_car_model(name="First", slug="first", sort_order=1)
    create_car_model(name="Inactive", slug="inactive", is_active=False)
    create_car_model(name="Undetected", slug="undetected", detection_status=CarModel3D.DetectionStatus.FAILED)

    response = api_client.get(CAR_MODELS_URL)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(first.id), str(later.id)]


def test_car_model_api_returns_effective_manual_anchors_vehicle_names_and_credit(api_client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    generation = make_generation()
    car = create_car_model(
        name="BMW 3 Series",
        slug="bmw-3-series",
        wheel_anchors=ANCHORS,
        detection_status=CarModel3D.DetectionStatus.FAILED,
        detection_message="Manual positions were entered.",
        vehicle_model=generation.model,
        source_url="https://example.com/model",
    )

    item = api_client.get(CAR_MODELS_URL).json()[0]

    assert item == {
        "id": str(car.id),
        "name": "BMW 3 Series",
        "slug": "bmw-3-series",
        "body_type": "sedan",
        "glb_file": item["glb_file"],
        "length_m": "4.200",
        "front": "+z",
        "vehicle_model": {
            "id": str(generation.model_id),
            "name": generation.model.name,
            "make": generation.model.make.name,
        },
        "wheel_anchors": ANCHORS,
        "attribution": "Car model by Example, CC BY 4.0",
        "source_url": "https://example.com/model",
    }
    assert "/models3d/cars/car" in item["glb_file"]
    assert item["glb_file"].endswith(".glb")
