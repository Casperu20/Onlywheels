"""Small helpers to build test data. Each call creates new rows with unique slugs/SKUs."""

from datetime import datetime, timedelta
from decimal import Decimal
from itertools import count

from django.utils import timezone

from apps.appointments.services import available_slots
from apps.cart.services import add_item, get_cart
from apps.catalog.models import Brand, Product, ProductType, ProductVariant
from apps.fitment.models import FitmentSpec
from apps.garages.models import Garage
from apps.inventory.models import StockItem
from apps.orders.models import Order
from apps.vehicles.models import VehicleGeneration, VehicleMake, VehicleModel

_seq = count(1)


def make_garage(**fields) -> Garage:
    n = next(_seq)
    defaults = {
        "name": f"Garage {n}",
        "slug": f"garage-{n}",
        "city": "Cluj-Napoca",
        "county": "Cluj",
        "address": "Str. Test 1",
        "phone": "0740000000",
        "working_days": list(range(7)),
        "capacity_per_slot": 1,
        "fitting_price": Decimal("150.00"),
    }
    return Garage.objects.create(**{**defaults, **fields})


def future_slot(garage: Garage, days: int = 3) -> datetime:
    return available_slots(garage, timezone.localdate() + timedelta(days=days))[0][0]


def add_to_cart(user, variant: ProductVariant, quantity: int = 4) -> None:
    add_item(get_cart(user), variant, quantity)


def make_order(user, **fields) -> Order:
    n = next(_seq)
    defaults = {
        "number": f"OWTEST-{n}",
        "delivery_method": Order.Delivery.COURIER,
        "email": user.email,
        "full_name": "Ana Pop",
        "phone": "0712345678",
        "line1": "Str. Exemplu 1",
        "city": "Cluj-Napoca",
        "county": "Cluj",
        "postal_code": "400000",
        "subtotal": Decimal("100.00"),
        "total": Decimal("100.00"),
        "vat": Decimal("17.36"),
    }
    return Order.objects.create(user=user, **{**defaults, **fields})


def checkout_payload(**overrides) -> dict:
    return {
        "delivery_method": "courier",
        "email": "ana@example.com",
        "full_name": "Ana Pop",
        "phone": "0712345678",
        "line1": "Str. Exemplu 1",
        "city": "Cluj-Napoca",
        "county": "Cluj",
        "postal_code": "400000",
        "accept_terms": True,
        **overrides,
    }


def make_generation(
    *,
    name: str | None = None,
    pcd: str = "5x112",
    center_bore: str = "66.6",
    et: tuple[int, int] = (20, 40),
    diameter: tuple[int, int] = (17, 20),
    width: tuple[str, str] = ("7.5", "9.0"),
    thread: str = "M14x1.25",
    tires: tuple[str, ...] = ("225/45 R18", "225/40 R19"),
    with_fitment: bool = True,
) -> VehicleGeneration:
    n = next(_seq)
    make, _ = VehicleMake.objects.get_or_create(slug="bmw", defaults={"name": "BMW"})
    model, _ = VehicleModel.objects.get_or_create(
        make=make, slug="seria-3", defaults={"name": "Seria 3"}
    )
    generation = VehicleGeneration.objects.create(
        model=model, name=name or f"G{n}", year_from=2019
    )
    if with_fitment:
        FitmentSpec.objects.create(
            generation=generation,
            pcd=pcd,
            center_bore_mm=Decimal(center_bore),
            et_min=et[0],
            et_max=et[1],
            diameter_min=diameter[0],
            diameter_max=diameter[1],
            width_min=Decimal(width[0]),
            width_max=Decimal(width[1]),
            thread_size=thread,
            tire_sizes=list(tires),
        )
    return generation


def make_product(
    *, type: str = ProductType.WHEEL, name: str | None = None, brand: str = "BBS", **fields
) -> Product:
    n = next(_seq)
    brand_obj, _ = Brand.objects.get_or_create(slug=brand.lower().replace(" ", "-"), defaults={"name": brand})
    name = name or f"Product {n}"
    return Product.objects.create(
        type=type, brand=brand_obj, name=name, slug=f"{brand_obj.slug}-{n}", **fields
    )


WHEEL_DEFAULTS = {
    "finish": "silver",
    "diameter_in": 18,
    "width_in": Decimal("8.0"),
    "et_mm": 35,
    "pcd": "5x112",
    "center_bore_mm": Decimal("66.6"),
}


def make_variant(product: Product, *, price: str = "1000", stock: int = 10, **fields) -> ProductVariant:
    n = next(_seq)
    if product.type in (ProductType.WHEEL, ProductType.SET):
        fields = {**WHEEL_DEFAULTS, **fields}
    variant = ProductVariant.objects.create(
        product=product, sku=f"SKU-{n}", price=Decimal(price), **fields
    )
    StockItem.objects.create(variant=variant, quantity=stock)
    return variant


def make_tire(product: Product, size: tuple[int, int, int] = (225, 45, 18), **fields) -> ProductVariant:
    width, aspect, rim = size
    return make_variant(
        product, tire_width_mm=width, tire_aspect=aspect, diameter_in=rim, **fields
    )
