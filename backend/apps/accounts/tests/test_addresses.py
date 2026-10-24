import pytest

from apps.accounts.models import Address, User

pytestmark = pytest.mark.django_db

ADDRESS = {
    "full_name": "Ana Popescu",
    "phone": "0712345678",
    "line1": "Str. Exemplu 1",
    "city": "Cluj-Napoca",
    "county": "Cluj",
    "postal_code": "400000",
}


def test_create_and_list_own_addresses(auth_client, user):
    response = auth_client.post("/api/v1/accounts/addresses/", ADDRESS, format="json")
    assert response.status_code == 201

    response = auth_client.get("/api/v1/accounts/addresses/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert Address.objects.get().user == user


def test_cannot_see_other_users_addresses(auth_client):
    other = User.objects.create_user(email="other@example.com", password="x")
    address = Address.objects.create(user=other, **ADDRESS)

    assert auth_client.get("/api/v1/accounts/addresses/").json() == []
    assert auth_client.get(f"/api/v1/accounts/addresses/{address.id}/").status_code == 404


def test_only_one_default_address(auth_client, user):
    auth_client.post("/api/v1/accounts/addresses/", {**ADDRESS, "is_default": True}, format="json")
    auth_client.post("/api/v1/accounts/addresses/", {**ADDRESS, "is_default": True}, format="json")

    assert Address.objects.filter(user=user, is_default=True).count() == 1


def test_addresses_require_login(api_client):
    assert api_client.get("/api/v1/accounts/addresses/").status_code == 401
