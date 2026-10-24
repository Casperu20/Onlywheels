from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import User


@shared_task
def send_password_reset_email(user_id: str) -> None:
    from .services import build_password_reset_link

    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return

    context = {"user": user, "reset_link": build_password_reset_link(user)}
    send_mail(
        subject="OnlyWheels – resetare parolă / password reset",
        message=render_to_string("emails/password_reset.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
