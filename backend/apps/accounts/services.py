from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from .models import User
from .serializers import validate_new_password


def register_user(*, email: str, password: str, first_name: str = "", last_name: str = "") -> User:
    return User.objects.create_user(
        email=email, password=password, first_name=first_name, last_name=last_name
    )


def verify_google_credential(credential: str) -> dict:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise AuthenticationFailed("Google login is not configured.")
    try:
        info = id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError as exc:
        raise AuthenticationFailed("Invalid Google credential.") from exc
    if not info.get("email") or not info.get("email_verified"):
        raise AuthenticationFailed("Google account email is not verified.")
    return info


@transaction.atomic
def get_or_create_google_user(info: dict) -> User:
    sub = info["sub"]
    email = info["email"].lower()

    user = User.objects.filter(google_sub=sub).first()
    if user is None:
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=info.get("given_name", ""),
                last_name=info.get("family_name", ""),
            )
        user.google_sub = sub
        user.save(update_fields=["google_sub"])

    if not user.is_active:
        raise AuthenticationFailed("This account is disabled.")
    return user


def build_password_reset_link(user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"


def request_password_reset(email: str) -> None:
    from .tasks import send_password_reset_email

    user = User.objects.filter(email__iexact=email, is_active=True).first()
    # Always succeed silently so the endpoint can't be used to discover registered emails.
    if user is not None:
        transaction.on_commit(lambda: send_password_reset_email.delay(str(user.pk)))


def reset_password(*, uid: str, token: str, new_password: str) -> User:
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
        raise ValidationError({"token": ["Invalid or expired link."]}) from exc

    if not default_token_generator.check_token(user, token):
        raise ValidationError({"token": ["Invalid or expired link."]})

    validate_new_password(new_password, user, "new_password")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return user


# --- GDPR ------------------------------------------------------------------


def export_user_data(user: User) -> dict:
    """Everything we store about the user (GDPR art. 15/20), as JSON-serialisable data."""
    from apps.orders.models import Order

    orders = []
    for order in Order.objects.filter(user=user):
        orders.append(
            {
                **{f.attname: getattr(order, f.attname) for f in order._meta.concrete_fields},
                "items": list(order.items.values()),
            }
        )
    return {
        "exported_at": timezone.now(),
        "profile": {
            "id": user.pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "preferred_language": user.preferred_language,
            "google_login": bool(user.google_sub),
            "date_joined": user.date_joined,
            "last_login": user.last_login,
        },
        "addresses": list(user.addresses.values()),
        "vehicles": list(
            user.vehicles.values(
                "id",
                "nickname",
                "generation__model__make__name",
                "generation__model__name",
                "generation__name",
                "created_at",
            )
        ),
        "favorites": list(user.favorites.values("product__name", "product__slug", "created_at")),
        "reviews": list(
            user.reviews.values("product__name", "rating", "title", "body", "status", "created_at")
        ),
        "orders": orders,
    }


@transaction.atomic
def delete_account(user: User) -> None:
    """GDPR art. 17. Personal data is removed; orders stay (accounting law) but point to an anonymous user."""
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    from apps.cart.models import Cart
    from apps.reviews.services import recalculate_rating

    reviewed = [review.product for review in user.reviews.select_related("product")]
    user.reviews.all().delete()
    for product in reviewed:
        recalculate_rating(product)

    user.addresses.all().delete()
    user.vehicles.all().delete()
    user.favorites.all().delete()
    user.ai_generations.all().delete()
    Cart.objects.filter(user=user).delete()
    user.partner_garages.clear()
    user.groups.clear()
    user.user_permissions.clear()

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)

    user.history.all().delete()  # audit trail holds old emails/names
    user.email = f"deleted-{user.pk}@deleted.invalid"
    user.first_name = user.last_name = user.phone = ""
    user.google_sub = None
    user.is_active = user.is_staff = user.is_superuser = False
    user.set_unusable_password()
    user.save()
