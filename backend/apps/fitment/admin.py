from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import FitmentSpec


@admin.register(FitmentSpec)
class FitmentSpecAdmin(ModelAdmin):
    list_display = (
        "generation",
        "pcd",
        "center_bore_mm",
        "et_min",
        "et_max",
        "diameter_min",
        "diameter_max",
        "thread_size",
    )
    list_filter = ("pcd", "generation__model__make")
    search_fields = ("generation__name", "generation__model__name", "generation__model__make__name")
    autocomplete_fields = ("generation",)
