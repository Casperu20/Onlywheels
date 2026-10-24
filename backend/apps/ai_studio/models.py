from django.conf import settings
from django.db import models

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel


class AIGeneration(TimeStampedModel):
    class Source(models.TextChoices):
        RENDER_3D = "3d_render", "3D showroom render"
        USER_PHOTO = "user_photo", "Customer photo"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_generations")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    provider = models.CharField(max_length=30)
    source = models.CharField(max_length=20, choices=Source.choices)
    scene = models.CharField(max_length=60, blank=True, help_text="e.g. city-night, mountain-road")
    angle = models.CharField(max_length=30, blank=True)
    style = models.CharField(max_length=30, blank=True)
    input_image = models.ImageField(upload_to="ai/inputs/", blank=True)
    result_image = models.ImageField(upload_to="ai/results/", blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    cost = models.DecimalField(max_digits=8, decimal_places=4, default=0, help_text="Provider cost (USD)")
    error = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user} – {self.scene or self.source} ({self.status})"
