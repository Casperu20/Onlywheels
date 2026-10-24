from rest_framework import serializers

from .models import Garage


class GarageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Garage
        fields = (
            "id",
            "slug",
            "name",
            "city",
            "county",
            "address",
            "phone",
            "description",
            "latitude",
            "longitude",
            "opens_at",
            "closes_at",
            "working_days",
            "fitting_price",
        )


class SlotSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class SlotQuerySerializer(serializers.Serializer):
    date = serializers.DateField()
