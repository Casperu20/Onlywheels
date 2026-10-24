from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Garage


@admin.register(Garage)
class GarageAdmin(ModelAdmin):
    list_display = ("name", "city", "phone", "fitting_price", "capacity_per_slot", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name", "city", "address")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("partner_users",)
