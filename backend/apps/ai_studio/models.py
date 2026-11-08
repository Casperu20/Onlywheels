from django.conf import settings
from django.db import models

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel

from .storage import get_ai_storage, input_upload_to, result_upload_to


class AIGeneration(TimeStampedModel):
    class Source(models.TextChoices):
        RENDER_3D = "3d_render", "3D showroom render"
        USER_PHOTO = "user_photo", "Customer photo"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_generations")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    provider = models.CharField(max_length=30)
    source = models.CharField(max_length=20, choices=Source.choices)
    scene = models.CharField(max_length=60, blank=True, help_text="e.g. city_night, mountain_road")
    angle = models.CharField(max_length=30, blank=True)
    style = models.CharField(max_length=30, blank=True)
    input_image = models.ImageField(upload_to=input_upload_to, storage=get_ai_storage, blank=True)
    result_image = models.ImageField(upload_to=result_upload_to, storage=get_ai_storage, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    estimated_cost = models.DecimalField(
        max_digits=8, decimal_places=4, default=0, help_text="Estimate reserved from the daily budget (USD)"
    )
    cost = models.DecimalField(max_digits=8, decimal_places=4, default=0, help_text="Provider cost (USD)")
    budget_day = models.DateField(null=True, blank=True, help_text="Daily budget the estimate was reserved from")
    budget_settled = models.BooleanField(default=False)
    provider_job_id = models.CharField(max_length=120, blank=True)
    error = models.TextField(blank=True, help_text="Shown to the customer; keep it free of provider details")
    error_detail = models.TextField(blank=True, help_text="Staff-only diagnostic")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Deleted by the customer; images removed")

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "created_at"))]

    def __str__(self) -> str:
        return f"{self.user} – {self.scene or self.source} ({self.status})"


class AIDailyBudget(models.Model):
    """Global spend ceiling per local day; rows are locked with select_for_update when reserving."""

    day = models.DateField(unique=True)
    spent_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    reserved_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    class Meta:
        ordering = ("-day",)
        verbose_name = "AI daily budget"

    def __str__(self) -> str:
        return f"{self.day}: spent {self.spent_usd} + reserved {self.reserved_usd} USD"
