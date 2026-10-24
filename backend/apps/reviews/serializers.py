from rest_framework import serializers

from apps.catalog.models import Product

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "rating", "title", "body", "author", "is_verified_purchase", "status", "created_at")
        read_only_fields = fields

    def get_author(self, obj: Review) -> str:
        """Public display name: first name + last initial, e.g. "Ana P."."""
        user = obj.user
        if user.first_name:
            initial = f" {user.last_name[0]}." if user.last_name else ""
            return f"{user.first_name}{initial}"
        return user.email.split("@")[0][:3] + "…"


class ReviewCreateSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True), source="product"
    )
    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    body = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        user = self.context["request"].user
        if Review.objects.filter(user=user, product=attrs["product"]).exists():
            raise serializers.ValidationError({"product_id": ["You have already reviewed this product."]})
        return attrs
