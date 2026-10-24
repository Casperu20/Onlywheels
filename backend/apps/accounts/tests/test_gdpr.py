import pytest
from django.conf import settings

from apps.accounts.models import Address
from apps.cart.models import Cart
from apps.reviews.models import Favorite, Review
from apps.vehicles.models import UserVehicle
from tests.factories import add_to_cart, make_generation, make_order, make_product, make_variant

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Passw0rd!"  # same as the `user` fixture in conftest.py


@pytest.fixture
def user_data(user):
    product = make_product(name="BBS CH-R")
    variant = make_variant(product)
    Address.objects.create(
        user=user, full_name="Ana Pop", phone="0712345678", line1="Str. Exemplu 1",
        city="Cluj-Napoca", county="Cluj", postal_code="400000",
    )
    UserVehicle.objects.create(user=user, generation=make_generation(), nickname="Daily")
    Favorite.objects.create(user=user, product=product)
    Review.objects.create(user=user, product=product, rating=5, status=Review.Status.APPROVED)
    product.rating_count, product.rating_avg = 1, 5
    product.save()
    add_to_cart(user, variant, 1)
    order = make_order(user)
    return {"product": product, "order": order}


def test_export_contains_all_personal_data(auth_client, user, user_data):
    response = auth_client.get("/api/v1/auth/me/export/")

    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    data = response.json()
    assert data["profile"]["email"] == user.email
    assert data["addresses"][0]["line1"] == "Str. Exemplu 1"
    assert data["vehicles"][0]["nickname"] == "Daily"
    assert data["favorites"][0]["product__name"] == "BBS CH-R"
    assert data["reviews"][0]["rating"] == 5
    assert data["orders"][0]["number"] == user_data["order"].number


def test_export_requires_login(api_client):
    assert api_client.get("/api/v1/auth/me/export/").status_code == 401


def test_delete_requires_correct_password(auth_client, user):
    response = auth_client.post("/api/v1/auth/me/delete/", {"password": "wrong"}, format="json")

    assert response.status_code == 400
    assert "password" in response.json()["error"]["fields"]
    user.refresh_from_db()
    assert user.is_active


def test_delete_anonymises_user_and_keeps_orders(auth_client, user, user_data):
    response = auth_client.post("/api/v1/auth/me/delete/", {"password": PASSWORD}, format="json")

    assert response.status_code == 204
    assert response.cookies[settings.AUTH_COOKIE_ACCESS].value == ""
    user.refresh_from_db()
    assert not user.is_active
    assert user.email.endswith("@deleted.invalid")
    assert user.first_name == ""
    assert not user.has_usable_password()
    assert not user.addresses.exists()
    assert not user.vehicles.exists()
    assert not user.favorites.exists()
    assert not user.reviews.exists()
    assert not Cart.objects.filter(user=user).exists()
    assert user.orders.filter(pk=user_data["order"].pk).exists()
    assert not user.history.filter(email="ana@example.com").exists()

    user_data["product"].refresh_from_db()
    assert user_data["product"].rating_count == 0

    # The old session is dead and the old credentials no longer work.
    assert auth_client.post("/api/v1/auth/refresh/").status_code == 401
    login = auth_client.post(
        "/api/v1/auth/login/", {"email": "ana@example.com", "password": PASSWORD}, format="json"
    )
    assert login.status_code == 401


def test_google_only_account_confirms_with_email(auth_client, user):
    user.set_unusable_password()
    user.save()

    wrong = auth_client.post("/api/v1/auth/me/delete/", {"confirm_email": "x@y.z"}, format="json")
    assert wrong.status_code == 400
    assert "confirm_email" in wrong.json()["error"]["fields"]

    ok = auth_client.post("/api/v1/auth/me/delete/", {"confirm_email": "ANA@example.com"}, format="json")
    assert ok.status_code == 204
