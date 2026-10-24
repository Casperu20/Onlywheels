import pytest

from apps.orders.models import Order
from apps.orders.services import mark_paid
from apps.reviews.models import Review
from apps.reviews.services import moderate
from tests.factories import make_order, make_product, make_variant

pytestmark = pytest.mark.django_db

URL = "/api/v1/reviews/"


@pytest.fixture
def product():
    product = make_product()
    make_variant(product)
    return product


def post_review(client, product, **fields):
    return client.post(URL, {"product_id": str(product.pk), "rating": 4, "title": "Super", **fields}, format="json")


def test_review_requires_login(api_client, product):
    assert post_review(api_client, product).status_code == 401


def test_new_review_is_pending_until_approved(auth_client, api_client, product):
    response = post_review(auth_client, product)
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["author"] == "Ana"

    assert api_client.get(URL, {"product": product.slug}).json()["results"] == []

    moderate(Review.objects.get(), Review.Status.APPROVED)
    assert len(api_client.get(URL, {"product": product.slug}).json()["results"]) == 1
    product.refresh_from_db()
    assert (str(product.rating_avg), product.rating_count) == ("4.00", 1)


def test_one_review_per_product(auth_client, product):
    post_review(auth_client, product)
    response = post_review(auth_client, product)
    assert response.status_code == 400
    assert "product_id" in response.json()["error"]["fields"]


def test_verified_purchase(auth_client, user, product):
    order = make_order(user)
    order.items.create(
        variant=product.variants.first(),
        product_name=product.name,
        product_type=product.type,
        sku="X",
        unit_price=100,
        quantity=1,
        line_total=100,
    )
    mark_paid(order)
    assert Order.objects.get(pk=order.pk).status == "paid"

    assert post_review(auth_client, product).json()["is_verified_purchase"] is True


def test_rating_validation(auth_client, product):
    assert post_review(auth_client, product, rating=6).status_code == 400


def test_list_requires_product(api_client):
    assert api_client.get(URL).status_code == 400


def test_my_review(auth_client, product):
    assert auth_client.get(f"{URL}mine/", {"product": product.slug}).status_code == 404
    post_review(auth_client, product)
    assert auth_client.get(f"{URL}mine/", {"product": product.slug}).json()["status"] == "pending"
