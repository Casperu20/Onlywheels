import pytest

from apps.accounts.models import User
from apps.vehicles.models import UserVehicle
from tests.factories import make_generation

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vehicles"


def test_make_model_generation_cascade(api_client):
    generation = make_generation(name="G20 / G21")
    model = generation.model
    make = model.make

    makes = api_client.get(f"{BASE}/makes/").json()
    assert [m["slug"] for m in makes] == ["bmw"]

    models = api_client.get(f"{BASE}/models/", {"make": str(make.pk)}).json()
    assert [m["name"] for m in models] == ["Seria 3"]

    generations = api_client.get(f"{BASE}/generations/", {"model": str(model.pk)}).json()
    assert generations[0]["name"] == "G20 / G21"
    assert generations[0]["has_fitment"] is True
    assert generations[0]["make"]["name"] == "BMW"


def test_generation_detail_contains_fitment(api_client):
    generation = make_generation(pcd="5×112.0", tires=("225/45r18",))

    data = api_client.get(f"{BASE}/generations/{generation.pk}/").json()

    assert data["fitment"]["pcd"] == "5x112"
    assert data["fitment"]["tire_sizes"] == ["225/45 R18"]


def test_generation_without_fitment(api_client):
    generation = make_generation(with_fitment=False)

    data = api_client.get(f"{BASE}/generations/{generation.pk}/").json()

    assert data["has_fitment"] is False
    assert data["fitment"] is None


def test_my_garage_crud(auth_client, user):
    g1 = make_generation()
    g2 = make_generation()

    created = auth_client.post(
        f"{BASE}/my/", {"generation_id": str(g1.pk), "is_default": True}, format="json"
    )
    assert created.status_code == 201
    assert created.json()["generation"]["id"] == str(g1.pk)

    auth_client.post(f"{BASE}/my/", {"generation_id": str(g2.pk), "is_default": True}, format="json")
    assert UserVehicle.objects.filter(user=user, is_default=True).count() == 1

    duplicate = auth_client.post(f"{BASE}/my/", {"generation_id": str(g1.pk)}, format="json")
    assert duplicate.status_code == 400
    assert "generation_id" in duplicate.json()["error"]["fields"]

    vehicle_id = created.json()["id"]
    renamed = auth_client.patch(f"{BASE}/my/{vehicle_id}/", {"nickname": "Daily"}, format="json")
    assert renamed.json()["nickname"] == "Daily"

    assert auth_client.delete(f"{BASE}/my/{vehicle_id}/").status_code == 204
    assert len(auth_client.get(f"{BASE}/my/").json()) == 1


def test_my_garage_is_private(auth_client):
    other = User.objects.create_user(email="other@example.com", password="x")
    vehicle = UserVehicle.objects.create(user=other, generation=make_generation())

    assert auth_client.get(f"{BASE}/my/").json() == []
    assert auth_client.delete(f"{BASE}/my/{vehicle.pk}/").status_code == 404


def test_my_garage_requires_login(api_client):
    assert api_client.get(f"{BASE}/my/").status_code == 401
