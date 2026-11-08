import mimetypes

from django.contrib import admin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import AIDailyBudget, AIGeneration

IMAGE_FIELDS = {"input": "input_image", "result": "result_image"}


@admin.register(AIGeneration)
class AIGenerationAdmin(ModelAdmin):
    list_display = ("created_at", "user", "provider", "scene", "style", "status", "estimated_cost", "cost")
    list_filter = ("provider", "source", "status", "scene")
    search_fields = ("user__email", "provider_job_id")
    date_hierarchy = "created_at"
    exclude = ("input_image", "result_image")
    readonly_fields = (
        "user",
        "variant",
        "provider",
        "source",
        "scene",
        "angle",
        "style",
        "status",
        "input_link",
        "result_link",
        "estimated_cost",
        "cost",
        "budget_day",
        "budget_settled",
        "provider_job_id",
        "error",
        "error_detail",
        "started_at",
        "finished_at",
        "deleted_at",
    )

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        return [
            path(
                "<path:object_id>/image/<str:kind>/",
                self.admin_site.admin_view(self.image_view),
                name="ai_studio_aigeneration_image",
            ),
            *super().get_urls(),
        ]

    def image_view(self, request, object_id, kind):
        if kind not in IMAGE_FIELDS or not self.has_view_permission(request):
            raise Http404
        image = getattr(get_object_or_404(AIGeneration, pk=object_id), IMAGE_FIELDS[kind])
        if not image:
            raise Http404
        response = FileResponse(
            image.open("rb"), content_type=mimetypes.guess_type(image.name)[0] or "application/octet-stream"
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def _link(self, generation, kind):
        if not getattr(generation, IMAGE_FIELDS[kind]):
            return "—"
        url = reverse("admin:ai_studio_aigeneration_image", args=[generation.pk, kind])
        return format_html('<a href="{}" target="_blank" rel="noopener">Open</a>', url)

    @admin.display(description="Customer photo")
    def input_link(self, generation):
        return self._link(generation, "input")

    @admin.display(description="Result")
    def result_link(self, generation):
        return self._link(generation, "result")


@admin.register(AIDailyBudget)
class AIDailyBudgetAdmin(ModelAdmin):
    list_display = ("day", "spent_usd", "reserved_usd")
    readonly_fields = ("day", "spent_usd", "reserved_usd")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
