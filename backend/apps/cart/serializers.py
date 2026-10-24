from django.conf import settings
from rest_framework import serializers

from apps.catalog.serializers import VariantSerializer
from apps.inventory.models import available_for

from .models import CartItem
from .services import purchasable_variants


class CartProductSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    brand = serializers.CharField(source="brand.name")


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(source="variant.product", read_only=True)
    variant = VariantSerializer(read_only=True)
    unit_price = serializers.DecimalField(source="variant.price", max_digits=10, decimal_places=2, read_only=True)
    line_total = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ("id", "quantity", "unit_price", "line_total", "available", "product", "variant")

    def get_line_total(self, obj: CartItem) -> str:
        return f"{obj.variant.price * obj.quantity:.2f}"

    def get_available(self, obj: CartItem) -> int:
        return available_for(obj.variant)


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    item_count = serializers.IntegerField(help_text="Total number of pieces")


class AddItemSerializer(serializers.Serializer):
    variant_id = serializers.PrimaryKeyRelatedField(queryset=purchasable_variants(), source="variant")
    quantity = serializers.IntegerField(min_value=1, max_value=settings.CART_MAX_QUANTITY, default=1)


class UpdateItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=settings.CART_MAX_QUANTITY)


class MergeLineSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=settings.CART_MAX_QUANTITY)


class MergeSerializer(serializers.Serializer):
    items = MergeLineSerializer(many=True, max_length=100)
