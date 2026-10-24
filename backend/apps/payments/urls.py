from django.urls import path

from .views import FakePaymentCompleteView, StripeWebhookView

urlpatterns = [
    path("webhook/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("fake/complete/", FakePaymentCompleteView.as_view(), name="fake-payment-complete"),
]
