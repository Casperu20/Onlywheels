import uuid

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.fitment.services import get_spec

from .filters import ProductFilter
from .models import Brand, Category
from .selectors import annotate_listing, product_base
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


@extend_schema(tags=["catalog"])
class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.filter(products__is_active=True).distinct()
    serializer_class = BrandSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    lookup_field = "slug"


@extend_schema(tags=["catalog"])
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    lookup_field = "slug"


@extend_schema_view(
    retrieve=extend_schema(
        parameters=[
            OpenApiParameter(
                "vehicle",
                OpenApiTypes.UUID,
                description="Vehicle generation id: adds a `fitment` result to every variant",
            )
        ]
    )
)
@extend_schema(tags=["catalog"])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    lookup_field = "slug"
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ProductFilter

    def get_queryset(self):
        queryset = product_base()
        if self.action == "retrieve":
            return annotate_listing(queryset, user=self.request.user)
        # The list is annotated by ProductFilter, together with the variant filters.
        return queryset

    def filter_queryset(self, queryset):
        if self.action == "retrieve":
            return queryset
        return super().filter_queryset(queryset)

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        vehicle = self.request.query_params.get("vehicle") if self.request else None
        if self.action == "retrieve" and vehicle:
            try:
                context["fitment_spec"] = get_spec(uuid.UUID(vehicle))
            except ValueError:
                pass
        return context
