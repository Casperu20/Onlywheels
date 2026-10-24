from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel
from apps.vehicles.models import VehicleGeneration

from .normalize import normalize_pcd, normalize_thread, normalize_tire_size


class FitmentSpec(TimeStampedModel):
    """Wheel/tire constraints for one vehicle generation (demo data, see seed_vehicles)."""

    generation = models.OneToOneField(
        VehicleGeneration, on_delete=models.CASCADE, related_name="fitment"
    )
    pcd = models.CharField("PCD", max_length=20, help_text="Bolt pattern, e.g. 5x112")
    center_bore_mm = models.DecimalField(
        max_digits=5, decimal_places=1, help_text="Hub diameter of the car"
    )
    et_min = models.SmallIntegerField("ET min (mm)")
    et_max = models.SmallIntegerField("ET max (mm)")
    diameter_min = models.PositiveSmallIntegerField("Diameter min (in)")
    diameter_max = models.PositiveSmallIntegerField("Diameter max (in)")
    width_min = models.DecimalField("Width min (J)", max_digits=3, decimal_places=1)
    width_max = models.DecimalField("Width max (J)", max_digits=3, decimal_places=1)
    thread_size = models.CharField(max_length=20, blank=True, help_text="e.g. M14x1.5")
    tire_sizes = models.JSONField(
        default=list, blank=True, help_text='OEM tire sizes, e.g. ["225/45 R18", "225/40 R19"]'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("generation__model__make__name", "generation__model__name")

    def __str__(self) -> str:
        return f"{self.generation} – {self.pcd}, CB {self.center_bore_mm}"

    def clean(self) -> None:
        errors = {}
        try:
            self.pcd = normalize_pcd(self.pcd)
        except ValueError as exc:
            errors["pcd"] = str(exc)
        try:
            self.tire_sizes = [normalize_tire_size(s) for s in self.tire_sizes or []]
        except ValueError as exc:
            errors["tire_sizes"] = str(exc)
        if self.et_min is not None and self.et_max is not None and self.et_min > self.et_max:
            errors["et_max"] = "ET max must be >= ET min."
        if (
            self.diameter_min is not None
            and self.diameter_max is not None
            and self.diameter_min > self.diameter_max
        ):
            errors["diameter_max"] = "Diameter max must be >= diameter min."
        if self.width_min is not None and self.width_max is not None and self.width_min > self.width_max:
            errors["width_max"] = "Width max must be >= width min."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.pcd = normalize_pcd(self.pcd)
        self.tire_sizes = [normalize_tire_size(s) for s in self.tire_sizes or []]
        if self.thread_size:
            self.thread_size = normalize_thread(self.thread_size)
        super().save(*args, **kwargs)
