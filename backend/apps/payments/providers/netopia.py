from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlsplit

import requests
from django.conf import settings
from django.utils import timezone

from apps.orders.models import Order

from .base import CheckoutSession, PaymentProvider, PaymentProviderError


class NetopiaProvider(PaymentProvider):
    name = "netopia"

    def create_checkout(self, order: Order) -> CheckoutSession:
        mode = settings.NETOPIA_MODE
        api_urls = {
            "sandbox": "https://secure.sandbox.netopia-payments.com/payment/card/start",
            "live": "https://secure.mobilpay.ro/pay/payment/card/start",
        }
        api_url = api_urls.get(mode)
        if api_url is None:
            raise PaymentProviderError("NETOPIA mode must be either sandbox or live.")

        api_key = settings.NETOPIA_API_KEY.strip()
        pos_signature = settings.NETOPIA_POS_SIGNATURE.strip()
        notify_url = settings.NETOPIA_NOTIFY_URL.strip()
        if not api_key or not pos_signature or not notify_url:
            raise PaymentProviderError("NETOPIA checkout credentials and notification URL are required.")
        try:
            parsed_notify_url = urlsplit(notify_url)
        except ValueError as exc:
            raise PaymentProviderError("NETOPIA notification URL must be an absolute HTTPS URL.") from exc
        if parsed_notify_url.scheme != "https" or not parsed_notify_url.netloc:
            raise PaymentProviderError("NETOPIA notification URL must be an absolute HTTPS URL.")

        country_codes = {"RO": 642}
        country_code = country_codes.get(order.country.upper())
        if country_code is None:
            raise PaymentProviderError("NETOPIA checkout currently supports Romanian billing addresses only.")

        name_parts = order.full_name.split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        address = {
            "email": order.email,
            "phone": order.phone,
            "firstName": first_name,
            "lastName": last_name,
            "city": order.city,
            "country": country_code,
            "countryName": "Romania",
            "state": order.county,
            "postalCode": order.postal_code,
            "details": " ".join(part for part in (order.line1, order.line2) if part),
        }
        redirect_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}/checkout/success?"
            f"{urlencode({'order': order.number})}"
        )
        payload = {
            "config": {
                "notifyUrl": notify_url,
                "redirectUrl": redirect_url,
                "language": "ro",
            },
            "payment": {"options": {"installments": 0, "bonus": 0}},
            "order": {
                "posSignature": pos_signature,
                "dateTime": timezone.now().isoformat(),
                "description": f"OnlyWheels order {order.number}",
                "orderID": order.number,
                "amount": float(order.total),
                "currency": order.currency,
                "billing": address,
            },
        }

        try:
            response = requests.post(
                api_url,
                json=payload,
                headers={"Authorization": api_key},
                timeout=15,
            )
            response.raise_for_status()
            body = response.json()
        except requests.Timeout as exc:
            raise PaymentProviderError("NETOPIA checkout request timed out.") from exc
        except requests.RequestException as exc:
            raise PaymentProviderError("NETOPIA rejected or could not process the checkout request.") from exc
        except ValueError as exc:
            raise PaymentProviderError("NETOPIA returned an invalid checkout response.") from exc

        if not isinstance(body, dict) or body.get("error") is not None:
            raise PaymentProviderError("NETOPIA returned a provider error.")

        payment = body.get("payment")
        session_id = payment.get("ntpID") if isinstance(payment, dict) else None
        checkout_url = payment.get("paymentURL") if isinstance(payment, dict) else None
        response_amount = payment.get("amount") if isinstance(payment, dict) else None
        response_currency = payment.get("currency") if isinstance(payment, dict) else None
        if response_amount is not None:
            if isinstance(response_amount, bool) or not isinstance(response_amount, int | float):
                raise PaymentProviderError("NETOPIA returned an invalid checkout amount.")
            try:
                provider_amount = Decimal(str(response_amount))
            except InvalidOperation as exc:
                raise PaymentProviderError("NETOPIA returned an invalid checkout amount.") from exc
            if not provider_amount.is_finite() or provider_amount != order.total:
                raise PaymentProviderError("NETOPIA checkout amount does not match the order.")
        if response_currency is not None and (
            not isinstance(response_currency, str) or response_currency.upper() != order.currency.upper()
        ):
            raise PaymentProviderError("NETOPIA checkout currency does not match the order.")

        try:
            parsed_url = urlsplit(checkout_url) if isinstance(checkout_url, str) else None
        except ValueError:
            parsed_url = None
        if (
            not isinstance(session_id, str)
            or not session_id.strip()
            or parsed_url is None
            or parsed_url.scheme != "https"
            or not parsed_url.netloc
        ):
            raise PaymentProviderError("NETOPIA returned an invalid hosted checkout session.")

        return CheckoutSession(session_id=session_id, url=checkout_url)
