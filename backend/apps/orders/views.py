from django.db.models import Prefetch
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.cart import services as cart_services
from apps.payments.services import start_checkout

from . import services
from .models import Order, OrderItem
from .serializers import (
    CheckoutSerializer,
    CheckoutSessionSerializer,
    OrderDetailSerializer,
    OrderSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
)


@extend_schema(tags=["checkout"])
class CheckoutPreviewView(APIView):
    """Totals for the current cart (voucher, shipping/fitting, VAT) before placing the order."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(request=QuoteRequestSerializer, responses=QuoteSerializer)
    def post(self, request):
        serializer = QuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        items = list(cart_services.cart_items(cart_services.get_cart(request.user)))
        quote = services.build_quote(
            items,
            delivery_method=data["delivery_method"],
            garage=data.get("garage"),
            voucher_code=data.get("voucher_code", ""),
        )
        return Response(QuoteSerializer(quote).data)


@extend_schema(tags=["orders"])
class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    lookup_field = "number"
    throttle_scope = "checkout"

    def get_throttles(self):
        if self.action in ("create", "pay"):
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related(
            Prefetch("items", queryset=OrderItem.objects.order_by("created_at")),
            "status_changes",
            "appointment__garage",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return OrderSerializer
        if self.action == "create":
            return CheckoutSerializer
        return OrderDetailSerializer

    @extend_schema(request=CheckoutSerializer, responses={201: OrderDetailSerializer})
    def create(self, request, *args, **kwargs):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.place_order(request.user, serializer.validated_data)
        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=CheckoutSessionSerializer)
    @action(detail=True, methods=["post"])
    def pay(self, request, number=None):
        """Start (or restart) the online payment; redirect the browser to `checkout_url`."""
        order = self.get_object()
        reservation_valid = order.reserved_until and order.reserved_until > timezone.now()
        if order.status != Order.Status.PENDING_PAYMENT or not reservation_valid:
            raise ValidationError({"non_field_errors": ["This order can no longer be paid."]})
        session = start_checkout(order)
        return Response(CheckoutSessionSerializer({"checkout_url": session.url}).data)

    @extend_schema(request=None, responses=OrderDetailSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, number=None):
        order = self.get_object()
        if order.status != Order.Status.PENDING_PAYMENT:
            raise ValidationError({"non_field_errors": ["Only unpaid orders can be cancelled online."]})
        services.cancel_order(order, note="Cancelled by customer", by=request.user)
        return Response(OrderDetailSerializer(self.get_queryset().get(pk=order.pk)).data)
