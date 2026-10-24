"""
Netopia Payments (phase 2) – Romanian card processor with installment support.

How it would plug in:
1. Add `NetopiaProvider` to `PROVIDERS` in `providers/__init__.py` and set PAYMENT_PROVIDER=netopia.
2. `create_checkout` calls Netopia's v2 API `POST /payment/card/start` with order number, amount,
   customer billing data and `notifyUrl=/api/v1/payments/webhook/netopia/`; it returns a
   `paymentURL` for the redirect.
3. Installments ("rate fără dobândă"): pass the `installments` option for eligible bank cards;
   store the chosen plan on Payment.
4. Add a `NetopiaWebhookView` that verifies the request signature with the merchant public key,
   records the event in WebhookEvent (idempotency) and calls `orders.services.mark_paid`
   when status = 3 (paid) / 5 (confirmed).
"""

from apps.orders.models import Order

from .base import CheckoutSession, PaymentProvider


class NetopiaProvider(PaymentProvider):
    name = "netopia"

    def create_checkout(self, order: Order) -> CheckoutSession:
        raise NotImplementedError("Netopia is planned for phase 2 (see module docstring).")
