from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import Brand, Category, Product, ProductType, ProductVariant
from apps.inventory.models import StockItem

# DEMO DATA – fictional prices and stock (same spirit as docs/prototype/index.html).

BRANDS = ["BBS", "OZ Racing", "Vossen", "Borbet", "AEZ", "Continental", "Michelin", "OnlyWheels"]

CATEGORIES = [
    ("jante-aliaj", "Jante aliaj", ProductType.WHEEL),
    ("anvelope-vara", "Anvelope de vară", ProductType.TIRE),
    ("anvelope-iarna", "Anvelope de iarnă", ProductType.TIRE),
    ("roti-complete", "Roți complete", ProductType.SET),
    ("prezoane", "Prezoane și piulițe", ProductType.ACCESSORY),
    ("inele-centrare", "Inele de centrare", ProductType.ACCESSORY),
]


def wheel(sku, finish, dia, width, et, pcd, bore, price, stock, old=None):
    return {
        "sku": sku, "finish": finish, "diameter_in": dia, "width_in": Decimal(width), "et_mm": et,
        "pcd": pcd, "center_bore_mm": Decimal(bore), "price": Decimal(price),
        "old_price": Decimal(old) if old else None, "stock": stock,
    }


def tire(sku, width, aspect, rim, load, speed, season, price, stock):
    return {
        "sku": sku, "tire_width_mm": width, "tire_aspect": aspect, "diameter_in": rim,
        "load_index": load, "speed_rating": speed, "season": season, "price": Decimal(price),
        "stock": stock,
    }


def wheel_set(sku, finish, dia, width, et, pcd, bore, tire_w, tire_a, price, stock):
    variant = wheel(sku, finish, dia, width, et, pcd, bore, price, stock)
    variant.update({"tire_width_mm": tire_w, "tire_aspect": tire_a, "season": "summer"})
    return variant


def accessory(sku, label, price, stock, thread=""):
    return {"sku": sku, "label": label, "thread_size": thread, "price": Decimal(price), "stock": stock}


PRODUCTS = [
    {
        "type": ProductType.WHEEL, "brand": "BBS", "category": "jante-aliaj", "name": "CH-R",
        "style": "multi-spoke", "badge": "Bestseller", "featured": True,
        "description": "Jantă turnată cu design multispiță, inspirată din motorsport.",
        "variants": [
            wheel("BBS-CHR-18-80-35-5112", "silver", 18, "8.0", 35, "5x112", "82.0", "1690", 12),
            wheel("BBS-CHR-19-85-35-5112", "silver", 19, "8.5", 35, "5x112", "82.0", "1890", 16),
            wheel("BBS-CHR-19-85-35-5120", "silver", 19, "8.5", 35, "5x120", "82.0", "1890", 8),
        ],
    },
    {
        "type": ProductType.WHEEL, "brand": "OZ Racing", "category": "jante-aliaj",
        "name": "Ultraleggera", "style": "Y-spoke", "badge": "Selecția noastră", "featured": True,
        "description": "Jantă ușoară, cu spițe în Y, pentru un look sport.",
        "variants": [
            wheel("OZ-ULT-17-75-45-5112", "black", 17, "7.5", 45, "5x112", "75.0", "1290", 20),
            wheel("OZ-ULT-18-80-45-5112", "black", 18, "8.0", 45, "5x112", "75.0", "1490", 16),
            wheel("OZ-ULT-18-80-35-5112", "black", 18, "8.0", 35, "5x112", "75.0", "1490", 12),
            wheel("OZ-ULT-18-80-35-5120", "black", 18, "8.0", 35, "5x120", "79.0", "1490", 8),
        ],
    },
    {
        "type": ProductType.WHEEL, "brand": "Vossen", "category": "jante-aliaj", "name": "HF-5",
        "style": "split-spoke", "badge": "Design nou", "featured": True,
        "description": "Design hibrid forjat, pentru mașini premium.",
        "variants": [
            wheel("VOS-HF5-19-85-35-5112", "bronze", 19, "8.5", 35, "5x112", "66.6", "2250", 8),
            wheel("VOS-HF5-20-90-32-5112", "bronze", 20, "9.0", 32, "5x112", "66.6", "2450", 8),
            wheel("VOS-HF5-20-90-32-5112-GM", "gunmetal", 20, "9.0", 32, "5x112", "66.6", "2450", 4),
        ],
    },
    {
        "type": ProductType.WHEEL, "brand": "Borbet", "category": "jante-aliaj", "name": "Y",
        "style": "Y-spoke", "badge": "Ofertă", "featured": True,
        "description": "Clasic, robust și accesibil.",
        "variants": [
            wheel("BOR-Y-17-75-45-5112", "silver", 17, "7.5", 45, "5x112", "57.1", "790", 24, old="920"),
            wheel("BOR-Y-18-80-40-5112", "silver", 18, "8.0", 40, "5x112", "66.6", "890", 24, old="1050"),
            wheel("BOR-Y-18-80-35-5120", "silver", 18, "8.0", 35, "5x120", "72.6", "890", 12, old="1050"),
        ],
    },
    {
        "type": ProductType.WHEEL, "brand": "AEZ", "category": "jante-aliaj", "name": "Steam",
        "style": "5-spoke",
        "description": "Cinci spițe late, finisaj gunmetal.",
        "variants": [
            wheel("AEZ-STM-18-80-45-5112", "gunmetal", 18, "8.0", 45, "5x112", "66.5", "990", 16),
            wheel("AEZ-STM-19-85-40-5112", "gunmetal", 19, "8.5", 40, "5x112", "66.5", "1150", 12),
        ],
    },
    {
        "type": ProductType.WHEEL, "brand": "OZ Racing", "category": "jante-aliaj",
        "name": "Superturismo GT", "style": "multi-spoke",
        "description": "Inspirată din competițiile de turisme.",
        "variants": [
            wheel("OZ-STG-17-70-45-5112", "white", 17, "7.0", 45, "5x112", "75.0", "1090", 8),
            wheel("OZ-STG-18-80-48-5112", "black", 18, "8.0", 48, "5x112", "75.0", "1190", 12),
        ],
    },
    {
        "type": ProductType.TIRE, "brand": "Continental", "category": "anvelope-vara",
        "name": "PremiumContact 7", "badge": "Vară", "featured": True,
        "description": "Anvelopă de vară confortabilă, cu frânare scurtă pe ud.",
        "variants": [
            tire("CON-PC7-2055516", 205, 55, 16, 91, "V", "summer", "420", 40),
            tire("CON-PC7-2255017", 225, 50, 17, 98, "Y", "summer", "560", 32),
            tire("CON-PC7-2254518", 225, 45, 18, 95, "Y", "summer", "650", 32),
            tire("CON-PC7-2254019", 225, 40, 19, 93, "Y", "summer", "780", 16),
        ],
    },
    {
        "type": ProductType.TIRE, "brand": "Michelin", "category": "anvelope-vara",
        "name": "Pilot Sport 5", "badge": "Sport",
        "description": "Aderență sportivă și durată de viață mare.",
        "variants": [
            tire("MIC-PS5-2254517", 225, 45, 17, 94, "Y", "summer", "640", 24),
            tire("MIC-PS5-2254018", 225, 40, 18, 92, "Y", "summer", "720", 24),
            tire("MIC-PS5-2454018", 245, 40, 18, 97, "Y", "summer", "790", 16),
            tire("MIC-PS5-2354019", 235, 40, 19, 96, "Y", "summer", "850", 16),
        ],
    },
    {
        "type": ProductType.TIRE, "brand": "Continental", "category": "anvelope-iarna",
        "name": "WinterContact TS 870 P",
        "description": "Anvelopă de iarnă pentru zăpadă și drumuri reci.",
        "variants": [
            tire("CON-TS870-2055516", 205, 55, 16, 91, "H", "winter", "390", 32),
            tire("CON-TS870-2255017", 225, 50, 17, 98, "V", "winter", "480", 24),
            tire("CON-TS870-2254518", 225, 45, 18, 95, "V", "winter", "560", 16),
        ],
    },
    {
        "type": ProductType.TIRE, "brand": "Michelin", "category": "anvelope-iarna",
        "name": "Pilot Alpin 5",
        "description": "Anvelopă de iarnă performantă pentru mașini puternice.",
        "variants": [
            tire("MIC-PA5-2454518", 245, 45, 18, 100, "V", "winter", "890", 8),
            tire("MIC-PA5-2254019", 225, 40, 19, 93, "V", "winter", "930", 8),
        ],
    },
    {
        "type": ProductType.SET, "brand": "OnlyWheels", "category": "roti-complete",
        "name": "Urban Silver", "badge": "Set complet", "featured": True,
        "description": "4 jante 18\" + 4 anvelope de vară, montate și echilibrate.",
        "variants": [
            wheel_set("OW-SET-URB-18", "silver", 18, "8.0", 40, "5x112", "66.6", 225, 45, "7200", 4),
        ],
    },
    {
        "type": ProductType.SET, "brand": "OnlyWheels", "category": "roti-complete",
        "name": "Sport Graphite", "badge": "Set complet",
        "description": "4 jante 19\" + 4 anvelope de vară, montate și echilibrate.",
        "variants": [
            wheel_set("OW-SET-SPG-19", "black", 19, "8.5", 35, "5x112", "66.6", 225, 40, "9800", 3),
        ],
    },
    {
        "type": ProductType.ACCESSORY, "brand": "OnlyWheels", "category": "prezoane",
        "name": "Kit prezoane", "badge": "Accesorii",
        "description": "Set de 20 prezoane cu cap conic 60°.",
        "variants": [
            accessory("OW-BOLT-M14150", "20 buc · M14×1.5", "190", 50, thread="M14x1.5"),
            accessory("OW-BOLT-M14125", "20 buc · M14×1.25", "190", 50, thread="M14x1.25"),
        ],
    },
    {
        "type": ProductType.ACCESSORY, "brand": "OnlyWheels", "category": "inele-centrare",
        "name": "Inele de centrare", "badge": "Accesorii",
        "description": "Set de 4 inele pentru jante cu alezaj mai mare decât butucul.",
        "variants": [
            accessory("OW-RING-820-666", "Set 4 · 82.0 → 66.6 mm", "80", 30),
            accessory("OW-RING-750-571", "Set 4 · 75.0 → 57.1 mm", "80", 30),
            accessory("OW-RING-726-666", "Set 4 · 72.6 → 66.6 mm", "80", 30),
        ],
    },
]


class Command(BaseCommand):
    help = "Create/update demo brands, categories, products, variants and stock. Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        brands = {
            name: Brand.objects.update_or_create(slug=slugify(name), defaults={"name": name})[0]
            for name in BRANDS
        }
        categories = {}
        for position, (slug, name, product_type) in enumerate(CATEGORIES):
            categories[slug], _ = Category.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "product_type": product_type, "position": position},
            )

        variant_count = 0
        for data in PRODUCTS:
            product, _ = Product.objects.update_or_create(
                slug=slugify(f"{data['brand']} {data['name']}"),
                defaults={
                    "type": data["type"],
                    "brand": brands[data["brand"]],
                    "category": categories[data["category"]],
                    "name": data["name"],
                    "style": data.get("style", ""),
                    "badge": data.get("badge", ""),
                    "description": data.get("description", ""),
                    "is_featured": data.get("featured", False),
                    "is_active": True,
                },
            )
            for variant_data in data["variants"]:
                fields = dict(variant_data)
                stock = fields.pop("stock")
                sku = fields.pop("sku")
                variant, _ = ProductVariant.objects.update_or_create(
                    sku=sku, defaults={**fields, "product": product, "is_active": True}
                )
                StockItem.objects.update_or_create(variant=variant, defaults={"quantity": stock})
                variant_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(PRODUCTS)} products with {variant_count} variants.")
        )
