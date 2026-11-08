import io

from django.conf import settings
from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

from apps.catalog.models import ProductVariant

from .models import AIGeneration
from .options import SCENE_CHOICES, STYLE_CHOICES, WHEEL_TYPES

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def normalise_photo(upload) -> bytes:
    """Validate an uploaded photo and re-encode it as a metadata-free JPEG (EXIF/GPS dropped)."""
    if upload.size > settings.AI_STUDIO_MAX_UPLOAD_BYTES:
        limit_mb = settings.AI_STUDIO_MAX_UPLOAD_BYTES / (1024 * 1024)
        raise serializers.ValidationError(f"The photo is too large; the limit is {limit_mb:g} MB.")
    try:
        upload.seek(0)
        image = Image.open(upload)
        if image.format not in ALLOWED_FORMATS:
            raise serializers.ValidationError("Upload a JPEG, PNG or WebP photo.")
        width, height = image.size
        if width * height > settings.AI_STUDIO_MAX_PIXELS:
            raise serializers.ValidationError("The photo has too many pixels; use a smaller image.")
        if min(width, height) < settings.AI_STUDIO_MIN_SIDE_PX:
            raise serializers.ValidationError(
                f"The photo is too small; use at least {settings.AI_STUDIO_MIN_SIDE_PX} px per side."
            )
        image.load()
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.thumbnail((settings.AI_STUDIO_MAX_SIDE_PX, settings.AI_STUDIO_MAX_SIDE_PX))
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=90, optimize=True)
        return output.getvalue()
    except serializers.ValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as exc:
        raise serializers.ValidationError("The file is not a readable image.") from exc


class AIGenerationCreateSerializer(serializers.Serializer):
    image = serializers.FileField()
    scene = serializers.ChoiceField(choices=SCENE_CHOICES)
    style = serializers.ChoiceField(choices=STYLE_CHOICES, default="photo")
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.filter(is_active=True, product__is_active=True, product__type__in=WHEEL_TYPES),
        required=False,
        allow_null=True,
        error_messages={"does_not_exist": "Choose an active wheel or wheel set."},
    )

    def validate_image(self, upload) -> bytes:
        return normalise_photo(upload)


class AIGenerationSerializer(serializers.ModelSerializer):
    variant_name = serializers.SerializerMethodField()
    input_url = serializers.SerializerMethodField()
    result_url = serializers.SerializerMethodField()

    class Meta:
        model = AIGeneration
        fields = (
            "id",
            "status",
            "scene",
            "style",
            "variant",
            "variant_name",
            "error",
            "input_url",
            "result_url",
            "created_at",
            "finished_at",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_variant_name(self, generation) -> str | None:
        variant = generation.variant
        if variant is None:
            return None
        return f"{variant.product} {variant.summary()}".strip()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_input_url(self, generation) -> str | None:
        return reverse("ai-generation-input", args=[generation.pk]) if generation.input_image else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_result_url(self, generation) -> str | None:
        return reverse("ai-generation-result", args=[generation.pk]) if generation.result_image else None


class ChoiceOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class AIStudioInfoSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    daily_limit = serializers.IntegerField()
    remaining_today = serializers.IntegerField()
    max_upload_bytes = serializers.IntegerField()
    retention_days = serializers.IntegerField()
    scenes = ChoiceOptionSerializer(many=True)
    styles = ChoiceOptionSerializer(many=True)
