from django.db.models import Exists, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product
from apps.catalog.selectors import annotate_listing, product_base
from apps.catalog.serializers import ProductListSerializer

from . import services
from .models import Favorite, Review
from .serializers import ReviewCreateSerializer, ReviewSerializer

PRODUCT_PARAM = OpenApiParameter("product", OpenApiTypes.STR, required=True, description="Product slug")


@extend_schema(tags=["reviews"])
class ReviewListCreateView(generics.ListCreateAPIView):
    """GET: approved reviews of a product. POST: submit a review (published after moderation)."""

    serializer_class = ReviewSerializer

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Review.objects.none()
        slug = self.request.query_params.get("product")
        if not slug:
            raise ValidationError({"product": ["This query parameter is required."]})
        return Review.objects.filter(
            product__slug=slug, status=Review.Status.APPROVED
        ).select_related("user")

    @extend_schema(parameters=[PRODUCT_PARAM])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(request=ReviewCreateSerializer, responses={201: ReviewSerializer})
    def post(self, request, *args, **kwargs):
        serializer = ReviewCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        review = services.create_review(
            request.user, data["product"], rating=data["rating"], title=data["title"], body=data["body"]
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["reviews"])
class MyReviewView(APIView):
    """The current user's review for a product (any status), so the UI can show "pending"."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(parameters=[PRODUCT_PARAM], responses=ReviewSerializer)
    def get(self, request):
        review = get_object_or_404(
            Review.objects.select_related("user"),
            user=request.user,
            product__slug=request.query_params.get("product", ""),
        )
        return Response(ReviewSerializer(review).data)


@extend_schema(tags=["favorites"])
class FavoriteListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()
        favorites = Favorite.objects.filter(user=self.request.user, product=OuterRef("pk"))
        products = product_base().filter(Exists(favorites))
        return annotate_listing(products, user=self.request.user).annotate(
            favorited_at=Subquery(favorites.values("created_at")[:1])
        ).order_by("-favorited_at")


@extend_schema(tags=["favorites"])
class FavoriteDetailView(APIView):
    """PUT adds a product to favorites, DELETE removes it. Both are idempotent."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(request=None, responses={204: None})
    def put(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        Favorite.objects.get_or_create(user=request.user, product=product)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={204: None})
    def delete(self, request, product_id):
        Favorite.objects.filter(user=request.user, product_id=product_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
