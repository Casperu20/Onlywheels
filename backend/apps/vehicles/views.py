import uuid

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from . import wheelsize
from .models import UserVehicle, VehicleGeneration, VehicleMake, VehicleModel
from .serializers import (
    GenerationDetailSerializer,
    GenerationSerializer,
    MakeSerializer,
    UserVehicleSerializer,
    VehicleModelSerializer,
)


class PublicListMixin:
    permission_classes = (AllowAny,)
    pagination_class = None


@extend_schema(tags=["vehicles"])
class MakeListView(PublicListMixin, generics.ListAPIView):
    serializer_class = MakeSerializer

    def get_queryset(self):
        wheelsize.ensure_makes()
        return VehicleMake.objects.all()


@extend_schema(tags=["vehicles"])
class ModelListView(PublicListMixin, generics.ListAPIView):
    serializer_class = VehicleModelSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("make",)

    def get_queryset(self):
        if make_id := _uuid(self.request.query_params.get("make")):
            wheelsize.ensure_models(make_id)
        return VehicleModel.objects.select_related("make")


def _uuid(value):
    try:
        return uuid.UUID(str(value)) if value else None
    except ValueError:
        return None


def _generations():
    return VehicleGeneration.objects.select_related("model__make", "fitment")


@extend_schema(tags=["vehicles"])
class GenerationListView(PublicListMixin, generics.ListAPIView):
    serializer_class = GenerationSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("model",)

    def get_queryset(self):
        if model_id := _uuid(self.request.query_params.get("model")):
            wheelsize.ensure_generations(model_id)
        return _generations()


@extend_schema(tags=["vehicles"])
class GenerationDetailView(generics.RetrieveAPIView):
    serializer_class = GenerationDetailSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        if generation_id := _uuid(self.kwargs.get("pk")):
            wheelsize.ensure_fitment(generation_id)
        return _generations()


@extend_schema(tags=["vehicles"])
class UserVehicleViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """The user's saved cars ("Garajul meu")."""

    serializer_class = UserVehicleSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return UserVehicle.objects.none()
        return UserVehicle.objects.filter(user=self.request.user).select_related(
            "generation__model__make", "generation__fitment"
        )

    def perform_create(self, serializer):
        wheelsize.ensure_fitment(serializer.validated_data["generation"].pk)
        serializer.save(user=self.request.user)
