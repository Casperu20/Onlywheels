from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.catalog.models import Model3D, ProductType
from apps.reviews.models import Favorite
from tests.factories import make_generation, make_product, make_tire, make_variant

pytestmark = pytest.mark.django_db

URL = "/api/v1/catalog/products/"


def slugs(response) -> list[str]:
    assert response.status_code == 200, response.content
    return [p["slug"] for p in response.json()["results"]]


def test_list_is_public_and_shows_cheapest_price(api_client):
    product = make_product(name="CH-R")
    make_variant(product, price="1890", diameter_in=19)
    make_variant(product, price="1690", diameter_in=18, old_price=Decimal("1800"))

    data = api_client.get(URL).json()

    item = data["results"][0]
    assert data["count"] == 1
    assert item["min_price"] == "1690.00"
    assert item["old_price"] == "1800.00"
    assert item["cheapest_variant"]["diameter_in"] == 18
    assert item["diameters"] == [18, 19]
    assert item["is_favorite"] is False


def test_inactive_products_and_variants_are_hidden(api_client):
    make_variant(make_product(is_active=False))
    make_variant(make_product(), is_active=False)

    assert slugs(api_client.get(URL)) == []


def test_variant_filters_must_match_the_same_variant(api_client):
    product = make_product()
    make_variant(product, diameter_in=18, finish="silver")
    make_variant(product, diameter_in=19, finish="black")

    assert slugs(api_client.get(URL, {"diameter": "18", "finish": "black"})) == []
    assert slugs(api_client.get(URL, {"diameter": "18", "finish": "silver"})) == [product.slug]
    assert slugs(api_client.get(URL, {"diameter": "17,19"})) == [product.slug]


def test_price_reflects_filtered_variant(api_client):
    product = make_product()
    make_variant(product, price="1000", diameter_in=17)
    make_variant(product, price="1500", diameter_in=19)

    item = api_client.get(URL, {"diameter": "19"}).json()["results"][0]

    assert item["min_price"] == "1500.00"
    assert item["cheapest_variant"]["diameter_in"] == 19


def test_filter_by_type_and_brand(api_client):
    wheel = make_product(brand="BBS")
    tire = make_product(type=ProductType.TIRE, brand="Michelin")
    make_variant(wheel)
    make_tire(tire)

    assert slugs(api_client.get(URL, {"type": "tire"})) == [tire.slug]
    assert slugs(api_client.get(URL, {"brand": "bbs"})) == [wheel.slug]
    assert set(slugs(api_client.get(URL, {"brand": "bbs,michelin"}))) == {wheel.slug, tire.slug}


def test_price_range_and_in_stock(api_client):
    cheap = make_product()
    expensive = make_product()
    make_variant(cheap, price="500", stock=0)
    make_variant(expensive, price="2500")

    assert slugs(api_client.get(URL, {"price_max": "1000"})) == [cheap.slug]
    assert slugs(api_client.get(URL, {"price_min": "1000"})) == [expensive.slug]
    assert slugs(api_client.get(URL, {"in_stock": "true"})) == [expensive.slug]


def test_vehicle_filter_returns_only_fitting_products(api_client):
    generation = make_generation(pcd="5x112", center_bore="66.6")
    fits = make_product(name="Fits")
    wrong_pcd = make_product(name="Wrong PCD")
    make_variant(fits, pcd="5x112")
    make_variant(wrong_pcd, pcd="5x120")

    assert slugs(api_client.get(URL, {"vehicle": str(generation.pk)})) == [fits.slug]


def test_vehicle_without_fitment_data_returns_nothing(api_client):
    make_variant(make_product())
    generation = make_generation(with_fitment=False)

    assert slugs(api_client.get(URL, {"vehicle": str(generation.pk)})) == []


def test_ordering_by_price(api_client):
    a = make_product(name="A")
    b = make_product(name="B")
    make_variant(a, price="2000")
    make_variant(b, price="900")

    assert slugs(api_client.get(URL, {"ordering": "price"})) == [b.slug, a.slug]
    assert slugs(api_client.get(URL, {"ordering": "-price"})) == [a.slug, b.slug]


def test_search_by_name_brand_and_sku(api_client):
    product = make_product(name="Ultraleggera", brand="OZ Racing")
    variant = make_variant(product)
    make_variant(make_product(name="Other"))

    assert slugs(api_client.get(URL, {"search": "ultra"})) == [product.slug]
    assert slugs(api_client.get(URL, {"search": "oz rac"})) == [product.slug]
    assert slugs(api_client.get(URL, {"search": variant.sku.lower()})) == [product.slug]


def test_is_favorite_for_logged_in_user(auth_client, user):
    product = make_product()
    make_variant(product)
    Favorite.objects.create(user=user, product=product)

    assert auth_client.get(URL).json()["results"][0]["is_favorite"] is True


def test_detail_includes_variants_and_fitment(api_client):
    generation = make_generation(center_bore="66.6")
    product = make_product()
    make_variant(product, center_bore_mm=Decimal("72.6"))
    make_variant(product, pcd="5x120", price="1200")

    plain = api_client.get(f"{URL}{product.slug}/").json()
    assert len(plain["variants"]) == 2
    assert plain["variants"][0]["fitment"] is None
    assert plain["variants"][0]["available"] == 10

    data = api_client.get(f"{URL}{product.slug}/", {"vehicle": str(generation.pk)}).json()
    fitments = [v["fitment"] for v in data["variants"]]
    assert fitments[0] == {"fits": True, "needs_hub_rings": True, "issues": []}
    assert fitments[1]["fits"] is False
    assert "pcd_mismatch" in fitments[1]["issues"]


def test_detail_unknown_slug_is_404(api_client):
    response = api_client.get(f"{URL}does-not-exist/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_detail_model_3d_is_optional(api_client):
    product = make_product()
    make_variant(product)
    assert api_client.get(f"{URL}{product.slug}/").json()["model_3d"] is None

    Model3D.objects.create(
        product=product,
        glb_file=SimpleUploadedFile("wheel.glb", b"glTF"),
        finish_materials={"silver": {"color": "#c9ccd1"}},
    )
    data = api_client.get(f"{URL}{product.slug}/").json()["model_3d"]
    assert data["glb_file"].endswith(".glb")
    assert data["finish_materials"]["silver"]["color"] == "#c9ccd1"


def test_list_has_no_n_plus_one(api_client, django_assert_max_num_queries):
    for _ in range(5):
        product = make_product()
        make_variant(product)
        make_variant(product, diameter_in=19)

    with django_assert_max_num_queries(5):
        assert len(slugs(api_client.get(URL))) == 5
