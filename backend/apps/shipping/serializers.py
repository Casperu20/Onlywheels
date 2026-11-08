from rest_framework import serializers

from .models import Shipment


class ShipmentSummarySerializer(serializers.ModelSerializer):
    carrier_display = serializers.CharField(source="get_carrier_display", read_only=True)

    class Meta:
        model = Shipment
        fields = ("carrier", "carrier_display", "awb", "tracking_url", "status")
