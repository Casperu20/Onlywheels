from django.urls import path

from .views import FakePaymentCompleteView, NetopiaWebhookView, StripeWebhookView

urlpatterns = [
    path("webhook/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("webhook/netopia/", NetopiaWebhookView.as_view(), name="netopia-webhook"),
    path("fake/complete/", FakePaymentCompleteView.as_view(), name="fake-payment-complete"),
]
