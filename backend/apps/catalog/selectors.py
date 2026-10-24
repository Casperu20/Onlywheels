from django.db.models import Exists, OuterRef, Prefetch, QuerySet, Subquery, Value

from apps.inventory.models import in_stock_q
from apps.reviews.models import Favorite

from .models import Product, ProductVariant


def active_variants() -> QuerySet[ProductVariant]:
    return ProductVariant.objects.filter(is_active=True)


def product_base() -> QuerySet[Product]:
    """Active products with everything the list/detail serializers need, without N+1 queries."""
    return (
        Product.objects.filter(is_active=True)
        .select_related("brand", "category", "model_3d")
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=active_variants().select_related("stock").order_by("price", "sku"),
            ),
            "media",
        )
    )


def annotate_listing(
    products: QuerySet[Product],
    variants: QuerySet[ProductVariant] | None = None,
    user=None,
) -> QuerySet[Product]:
    """
    Keep products that have at least one variant in `variants` and annotate:
    cheapest_variant_id / min_price / min_price_old (cheapest matching variant), in_stock, is_favorite.
    All variant filters must be applied to `variants` so they match the *same* variant.
    """
    variants = active_variants() if variants is None else variants
    matching = variants.filter(product=OuterRef("pk"))
    cheapest = matching.order_by("price", "sku")

    products = products.filter(Exists(matching)).annotate(
        cheapest_variant_id=Subquery(cheapest.values("pk")[:1]),
        min_price=Subquery(cheapest.values("price")[:1]),
        min_price_old=Subquery(cheapest.values("old_price")[:1]),
        in_stock=Exists(matching.filter(in_stock_q())),
    )
    if user is not None and user.is_authenticated:
        favorites = Favorite.objects.filter(user=user, product=OuterRef("pk"))
        return products.annotate(is_favorite=Exists(favorites))
    return products.annotate(is_favorite=Value(False))
