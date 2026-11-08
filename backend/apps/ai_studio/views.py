import mimetypes

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import AIGeneration
from .options import SCENES, STYLES, options
from .serializers import AIGenerationCreateSerializer, AIGenerationSerializer, AIStudioInfoSerializer

IMAGE_RESPONSE = {(200, "image/*"): OpenApiResponse(OpenApiTypes.BINARY, description="Private image")}


class StudioInfoView(APIView):
    @extend_schema(responses=AIStudioInfoSerializer)
    def get(self, request):
        data = {
            "enabled": services.configured_provider() is not None,
            "daily_limit": settings.AI_STUDIO_DAILY_QUOTA,
            "remaining_today": services.remaining_quota(request.user),
            "max_upload_bytes": settings.AI_STUDIO_MAX_UPLOAD_BYTES,
            "retention_days": settings.AI_STUDIO_RETENTION_DAYS,
            "scenes": options(SCENES),
            "styles": options(STYLES),
        }
        return Response(AIStudioInfoSerializer(data).data)


class GenerationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AIGenerationSerializer
    filter_backends = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AIGeneration.objects.none()
        return (
            AIGeneration.objects.filter(user=self.request.user, deleted_at__isnull=True)
            .select_related("variant__product__brand")
            .order_by("-created_at")
        )

    @extend_schema(request=AIGenerationCreateSerializer, responses={202: AIGenerationSerializer})
    def create(self, request):
        serializer = AIGenerationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        generation = services.reserve_generation(
            request.user,
            image=data["image"],
            scene=data["scene"],
            style=data["style"],
            variant=data.get("variant"),
        )
        return Response(AIGenerationSerializer(generation).data, status=status.HTTP_202_ACCEPTED)

    def perform_destroy(self, instance):
        services.delete_generation(instance)

    @extend_schema(request=None, responses={202: AIGenerationSerializer})
    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        generation = services.retry_generation(self.get_object())
        return Response(AIGenerationSerializer(generation).data, status=status.HTTP_202_ACCEPTED)

    def _stream(self, pk, field_name: str):
        # Owners see their own images; staff may open any (e.g. from the admin) but never list them.
        queryset = AIGeneration.objects.filter(deleted_at__isnull=True)
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        generation = get_object_or_404(queryset, pk=pk)
        image = getattr(generation, field_name)
        if not image:
            raise Http404
        content_type = mimetypes.guess_type(image.name)[0] or "application/octet-stream"
        response = FileResponse(image.open("rb"), content_type=content_type)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Disposition"] = "inline"
        return response

    @extend_schema(responses=IMAGE_RESPONSE)
    @action(detail=True, methods=["get"], url_path="input", url_name="input")
    def input_image(self, request, pk=None):
        return self._stream(pk, "input_image")

    @extend_schema(responses=IMAGE_RESPONSE)
    @action(detail=True, methods=["get"], url_path="result", url_name="result")
    def result_image(self, request, pk=None):
        return self._stream(pk, "result_image")
