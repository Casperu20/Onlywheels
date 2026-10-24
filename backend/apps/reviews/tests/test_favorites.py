import uuid

import pytest

from apps.reviews.models import Favorite
from tests.factories import make_product, make_variant

pytestmark = pytest.mark.django_db

URL = "/api/v1/favorites/"


@pytest.fixture
def product():
    product = make_product()
    make_variant(product)
    return product


def test_favorites_require_login(api_client, product):
    assert api_client.get(URL).status_code == 401
    assert api_client.put(f"{URL}{product.pk}/").status_code == 401


def test_add_list_and_remove_favorite(auth_client, user, product):
    assert auth_client.put(f"{URL}{product.pk}/").status_code == 204
    assert auth_client.put(f"{URL}{product.pk}/").status_code == 204  # idempotent
    assert Favorite.objects.filter(user=user).count() == 1

    results = auth_client.get(URL).json()["results"]
    assert [p["slug"] for p in results] == [product.slug]
    assert results[0]["is_favorite"] is True

    assert auth_client.delete(f"{URL}{product.pk}/").status_code == 204
    assert auth_client.get(URL).json()["results"] == []


def test_cannot_favorite_unknown_product(auth_client):
    assert auth_client.put(f"{URL}{uuid.uuid4()}/").status_code == 404


def test_favorites_are_private(auth_client, product):
    from apps.accounts.models import User

    other = User.objects.create_user(email="other@example.com", password="x")
    Favorite.objects.create(user=other, product=product)

    assert auth_client.get(URL).json()["results"] == []
