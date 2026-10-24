from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class VehicleMake(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class VehicleModel(TimeStampedModel):
    make = models.ForeignKey(VehicleMake, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        ordering = ("make__name", "name")
        constraints = [
            models.UniqueConstraint(fields=["make", "slug"], name="uniq_vehicle_model_per_make"),
        ]

    def __str__(self) -> str:
        return f"{self.make} {self.name}"


class VehicleGeneration(TimeStampedModel):
    model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name="generations")
    name = models.CharField(max_length=100, help_text='Chassis code(s), e.g. "G20 / G21"')
    year_from = models.PositiveSmallIntegerField()
    year_to = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Empty = still produced")

    class Meta:
        ordering = ("model__make__name", "model__name", "-year_from")
        constraints = [
            models.UniqueConstraint(fields=["model", "name"], name="uniq_generation_per_model"),
        ]

    def __str__(self) -> str:
        years = f"{self.year_from}–{self.year_to or ''}"
        return f"{self.model} {self.name} ({years})"


class UserVehicle(TimeStampedModel):
    """A car saved in the user's "Garajul meu"."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vehicles"
    )
    generation = models.ForeignKey(VehicleGeneration, on_delete=models.CASCADE, related_name="+")
    nickname = models.CharField(max_length=60, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ("-is_default", "-created_at")
        constraints = [
            models.UniqueConstraint(fields=["user", "generation"], name="uniq_user_vehicle"),
        ]

    def __str__(self) -> str:
        return self.nickname or str(self.generation)

    def save(self, *args, **kwargs):
        if self.is_default:
            UserVehicle.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)
