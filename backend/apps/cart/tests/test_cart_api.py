import uuid

import pytest

from apps.accounts.models import User
from apps.cart.models import CartItem
from apps.cart.services import add_item, get_cart
from tests.factories import make_product, make_variant

pytestmark = pytest.mark.django_db

URL = "/api/v1/cart/"


@pytest.fixture
def variant():
    return make_variant(make_product(), price="250")


def test_cart_requires_login(api_client):
    assert api_client.get(URL).status_code == 401


def test_add_items_and_totals(auth_client, variant):
    response = auth_client.post(f"{URL}items/", {"variant_id": str(variant.pk), "quantity": 4}, format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["item_count"] == 4
    assert data["subtotal"] == "1000.00"
    assert data["items"][0]["line_total"] == "1000.00"
    assert data["items"][0]["product"]["slug"] == variant.product.slug

    data = auth_client.post(f"{URL}items/", {"variant_id": str(variant.pk), "quantity": 2}, format="json").json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 6


def test_quantity_is_capped(auth_client, user, variant):
    add_item(get_cart(user), variant, 15)
    add_item(get_cart(user), variant, 15)
    assert CartItem.objects.get().quantity == 20


def test_update_and_remove_item(auth_client, user, variant):
    item = add_item(get_cart(user), variant, 4)

    data = auth_client.patch(f"{URL}items/{item.pk}/", {"quantity": 2}, format="json").json()
    assert data["items"][0]["quantity"] == 2

    data = auth_client.delete(f"{URL}items/{item.pk}/").json()
    assert data["items"] == []


def test_cannot_touch_other_users_items(auth_client, variant):
    other = User.objects.create_user(email="other@example.com", password="x")
    item = add_item(get_cart(other), variant, 1)

    assert auth_client.delete(f"{URL}items/{item.pk}/").status_code == 404


def test_inactive_variant_cannot_be_added(auth_client):
    variant = make_variant(make_product(), is_active=False)
    response = auth_client.post(f"{URL}items/", {"variant_id": str(variant.pk)}, format="json")
    assert response.status_code == 400


def test_merge_guest_cart(auth_client, user, variant):
    add_item(get_cart(user), variant, 2)
    other = make_variant(make_product())

    data = auth_client.post(
        f"{URL}merge/",
        {
            "items": [
                {"variant_id": str(variant.pk), "quantity": 2},
                {"variant_id": str(other.pk), "quantity": 4},
                {"variant_id": str(uuid.uuid4()), "quantity": 1},
            ]
        },
        format="json",
    ).json()

    quantities = {i["variant"]["sku"]: i["quantity"] for i in data["items"]}
    assert quantities == {variant.sku: 4, other.sku: 4}


def test_clear_cart(auth_client, user, variant):
    add_item(get_cart(user), variant, 2)
    assert auth_client.delete(URL).json()["items"] == []
