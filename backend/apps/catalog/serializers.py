from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.fitment.services import check_variant
from apps.inventory.models import available_for

from .models import Brand, Category, Product, ProductMedia, ProductVariant


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "logo")


class BrandMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("name", "slug")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "product_type")


class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ("id", "image", "alt")


class FitmentResultSerializer(serializers.Serializer):
    fits = serializers.BooleanField()
    needs_hub_rings = serializers.BooleanField()
    issues = serializers.ListField(child=serializers.CharField())


class VariantSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()
    fitment = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "sku",
            "label",
            "price",
            "old_price",
            "finish",
            "diameter_in",
            "width_in",
            "et_mm",
            "pcd",
            "center_bore_mm",
            "tire_size",
            "tire_width_mm",
            "tire_aspect",
            "load_index",
            "speed_rating",
            "season",
            "thread_size",
            "available",
            "fitment",
        )

    def get_available(self, obj: ProductVariant) -> int:
        return available_for(obj)

    @extend_schema_field(FitmentResultSerializer(allow_null=True))
    def get_fitment(self, obj: ProductVariant):
        spec = self.context.get("fitment_spec")
        if spec is None:
            return None
        result = check_variant(spec, obj)
        return {"fits": result.fits, "needs_hub_rings": result.needs_hub_rings, "issues": list(result.issues)}


class ProductListSerializer(serializers.ModelSerializer):
    """Requires a queryset from selectors.product_base() + annotate_listing()."""

    brand = BrandMiniSerializer(read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    old_price = serializers.DecimalField(
        source="min_price_old", max_digits=10, decimal_places=2, read_only=True, allow_null=True
    )
    in_stock = serializers.BooleanField(read_only=True)
    is_favorite = serializers.BooleanField(read_only=True)
    image = serializers.SerializerMethodField()
    finishes = serializers.SerializerMethodField()
    diameters = serializers.SerializerMethodField()
    cheapest_variant = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "slug",
            "type",
            "name",
            "brand",
            "style",
            "badge",
            "rating_avg",
            "rating_count",
            "min_price",
            "old_price",
            "in_stock",
            "is_favorite",
            "image",
            "finishes",
            "diameters",
            "cheapest_variant",
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_image(self, obj: Product) -> str | None:
        media = obj.media.all()
        if not media:
            return None
        request = self.context.get("request")
        url = media[0].image.url
        return request.build_absolute_uri(url) if request else url

    def get_finishes(self, obj: Product) -> list[str]:
        return sorted({v.finish for v in obj.variants.all() if v.finish})

    def get_diameters(self, obj: Product) -> list[int]:
        return sorted({v.diameter_in for v in obj.variants.all() if v.diameter_in})

    @extend_schema_field(VariantSerializer(allow_null=True))
    def get_cheapest_variant(self, obj: Product):
        """Cheapest variant that matched the current filters (the one behind `min_price`)."""
        target = getattr(obj, "cheapest_variant_id", None)
        variant = next((v for v in obj.variants.all() if v.pk == target), None)
        if variant is None:
            return None
        return VariantSerializer(variant, context=self.context).data


class ProductDetailSerializer(ProductListSerializer):
    category = CategorySerializer(read_only=True)
    media = ProductMediaSerializer(many=True, read_only=True)
    variants = VariantSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = (*ProductListSerializer.Meta.fields, "description", "category", "media", "variants")
