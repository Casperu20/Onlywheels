import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.core.models import TimeStampedModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Email-based user. Roles (customer, garage_partner, staff) are Django groups."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    preferred_language = models.CharField(
        max_length=2, choices=[("ro", "Română"), ("en", "English")], default="ro"
    )
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)  # noqa: DJ001
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    history = HistoricalRecords(excluded_fields=["password", "last_login"])

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ("-date_joined",)

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Address(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32)
    line1 = models.CharField("Street and number", max_length=255)
    line2 = models.CharField("Building, apartment", max_length=255, blank=True)
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=2, default="RO")
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ("-is_default", "-created_at")
        verbose_name_plural = "addresses"

    def __str__(self) -> str:
        return f"{self.full_name}, {self.line1}, {self.city}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)
