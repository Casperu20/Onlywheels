from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AIGeneration


@admin.register(AIGeneration)
class AIGenerationAdmin(ModelAdmin):
    list_display = ("created_at", "user", "provider", "source", "scene", "status", "cost")
    list_filter = ("provider", "source", "status")
    search_fields = ("user__email",)
