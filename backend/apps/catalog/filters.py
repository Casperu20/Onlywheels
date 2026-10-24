from django.db.models import Exists, OuterRef, Q
from django_filters import rest_framework as filters

from apps.fitment.normalize import normalize_pcd, normalize_tire_size
from apps.fitment.services import compatible_variants_q, get_spec
from apps.inventory.models import in_stock_q

from .models import Finish, Product, ProductType, ProductVariant, Season
from .selectors import active_variants, annotate_listing


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


class ProductFilter(filters.FilterSet):
    """
    Product-level filters narrow products directly. Variant-level filters (diameter, finish,
    price, vehicle, ...) are combined in `filter_queryset` so they all apply to the same variant.
    """

    type = filters.ChoiceFilter(choices=ProductType.choices)
    brand = CharInFilter(field_name="brand__slug", lookup_expr="in", help_text="Brand slugs, comma separated")
    category = filters.CharFilter(field_name="category__slug")
    featured = filters.BooleanFilter(field_name="is_featured")
    search = filters.CharFilter(method="filter_search", help_text="Name, brand or exact SKU")

    diameter = NumberInFilter(method="variant_filter", help_text="Inches, comma separated")
    finish = CharInFilter(method="variant_filter", help_text=f"One of: {', '.join(Finish.values)}")
    season = filters.ChoiceFilter(choices=Season.choices, method="variant_filter")
    tire_size = filters.CharFilter(method="variant_filter", help_text="e.g. 225/45 R18")
    pcd = filters.CharFilter(method="variant_filter", help_text="e.g. 5x112")
    price_min = filters.NumberFilter(method="variant_filter")
    price_max = filters.NumberFilter(method="variant_filter")
    in_stock = filters.BooleanFilter(method="variant_filter")
    vehicle = filters.UUIDFilter(
        method="variant_filter", help_text="Vehicle generation id: only products that fit"
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("min_price", "price"),
            ("name", "name"),
            ("created_at", "newest"),
            ("rating_avg", "rating"),
        )
    )

    class Meta:
        model = Product
        fields: list[str] = []

    def variant_filter(self, queryset, name, value):
        # Applied all together in filter_queryset().
        return queryset

    def filter_search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        sku_match = ProductVariant.objects.filter(product=OuterRef("pk"), sku__iexact=value)
        return queryset.filter(
            Q(name__icontains=value) | Q(brand__name__icontains=value) | Q(Exists(sku_match))
        )

    def build_variants(self):
        data = self.form.cleaned_data
        variants = active_variants()

        if data.get("diameter"):
            variants = variants.filter(diameter_in__in=[int(d) for d in data["diameter"]])
        if data.get("finish"):
            variants = variants.filter(finish__in=data["finish"])
        if data.get("season"):
            variants = variants.filter(season=data["season"])
        if data.get("tire_size"):
            try:
                variants = variants.filter(tire_size=normalize_tire_size(data["tire_size"]))
            except ValueError:
                return None
        if data.get("pcd"):
            try:
                variants = variants.filter(pcd=normalize_pcd(data["pcd"]))
            except ValueError:
                return None
        if data.get("price_min") is not None:
            variants = variants.filter(price__gte=data["price_min"])
        if data.get("price_max") is not None:
            variants = variants.filter(price__lte=data["price_max"])
        if data.get("in_stock"):
            variants = variants.filter(in_stock_q())
        if data.get("vehicle"):
            spec = get_spec(data["vehicle"])
            if spec is None:
                return None
            variants = variants.filter(compatible_variants_q(spec))
        return variants

    def filter_queryset(self, queryset):
        variants = self.build_variants()
        if variants is None:
            return queryset.none()
        user = getattr(self.request, "user", None)
        queryset = annotate_listing(queryset, variants, user).order_by("-is_featured", "name")
        return super().filter_queryset(queryset)
