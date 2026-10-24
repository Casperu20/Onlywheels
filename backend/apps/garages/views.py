from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.appointments.services import available_slots

from .models import Garage
from .serializers import GarageSerializer, SlotQuerySerializer, SlotSerializer


@extend_schema(tags=["garages"])
class GarageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Garage.objects.filter(is_active=True)
    serializer_class = GarageSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    lookup_field = "slug"
    filterset_fields = ("city",)

    @extend_schema(
        parameters=[OpenApiParameter("date", OpenApiTypes.DATE, required=True)],
        responses=SlotSerializer(many=True),
    )
    @action(detail=True, methods=["get"])
    def slots(self, request, slug=None):
        """Free fitting slots for one day (respects lead time, opening hours and capacity)."""
        query = SlotQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        slots = available_slots(self.get_object(), query.validated_data["date"])
        return Response(SlotSerializer([{"start": s, "end": e} for s, e in slots], many=True).data)
