from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.fitment.models import FitmentSpec

from .models import UserVehicle, VehicleGeneration, VehicleMake, VehicleModel


def _fitment(generation: VehicleGeneration) -> FitmentSpec | None:
    try:
        return generation.fitment
    except ObjectDoesNotExist:
        return None


class MakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleMake
        fields = ("id", "name", "slug")


class VehicleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = ("id", "name", "slug", "make")


class FitmentSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitmentSpec
        fields = (
            "pcd",
            "center_bore_mm",
            "et_min",
            "et_max",
            "diameter_min",
            "diameter_max",
            "width_min",
            "width_max",
            "thread_size",
            "tire_sizes",
        )


class GenerationSerializer(serializers.ModelSerializer):
    make = MakeSerializer(source="model.make", read_only=True)
    model = VehicleModelSerializer(read_only=True)
    has_fitment = serializers.SerializerMethodField()

    class Meta:
        model = VehicleGeneration
        fields = ("id", "name", "year_from", "year_to", "make", "model", "has_fitment")

    def get_has_fitment(self, obj: VehicleGeneration) -> bool:
        return _fitment(obj) is not None


class GenerationDetailSerializer(GenerationSerializer):
    fitment = serializers.SerializerMethodField()

    class Meta(GenerationSerializer.Meta):
        fields = (*GenerationSerializer.Meta.fields, "fitment")

    @extend_schema_field(FitmentSpecSerializer(allow_null=True))
    def get_fitment(self, obj: VehicleGeneration):
        spec = _fitment(obj)
        return FitmentSpecSerializer(spec).data if spec else None


class UserVehicleSerializer(serializers.ModelSerializer):
    generation = GenerationSerializer(read_only=True)
    generation_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleGeneration.objects.all(), source="generation", write_only=True
    )

    class Meta:
        model = UserVehicle
        fields = ("id", "generation", "generation_id", "nickname", "is_default", "created_at")
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        generation = attrs.get("generation")
        user = self.context["request"].user
        if generation is not None:
            duplicates = UserVehicle.objects.filter(user=user, generation=generation)
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"generation_id": ["This car is already in your garage."]}
                )
        return attrs
