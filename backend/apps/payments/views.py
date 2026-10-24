import stripe
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from . import services


@extend_schema(exclude=True)
class StripeWebhookView(APIView):
    """Stripe → us. Authenticated by the Stripe-Signature header, not by cookies."""

    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = ()

    def post(self, request):
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = services.verify_stripe_event(request.body, signature)
        except (ValueError, stripe.SignatureVerificationError):
            return Response({"error": {"code": "invalid_signature", "message": "Invalid webhook."}}, status=400)
        services.handle_stripe_event(event)
        return Response({"received": True})


@extend_schema(tags=["payments"])
class FakePaymentCompleteView(APIView):
    """Only when PAYMENT_PROVIDER=fake (development): simulates a successful payment."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request=inline_serializer("FakePaymentRequest", {"order_number": serializers.CharField()}),
        responses=inline_serializer("FakePaymentResponse", {"status": serializers.CharField()}),
    )
    def post(self, request):
        if settings.PAYMENT_PROVIDER != "fake":
            raise Http404
        order = get_object_or_404(Order, number=request.data.get("order_number", ""), user=request.user)
        order = services.complete_fake_payment(order)
        return Response({"status": order.status}, status=status.HTTP_200_OK)
