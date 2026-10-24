from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from apps.fitment.models import FitmentSpec

from .models import UserVehicle, VehicleGeneration, VehicleMake, VehicleModel


class VehicleModelInline(TabularInline):
    model = VehicleModel
    extra = 0
    prepopulated_fields = {"slug": ("name",)}


@admin.register(VehicleMake)
class VehicleMakeAdmin(ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = (VehicleModelInline,)


@admin.register(VehicleModel)
class VehicleModelAdmin(ModelAdmin):
    list_display = ("name", "make")
    list_filter = ("make",)
    search_fields = ("name", "make__name")
    prepopulated_fields = {"slug": ("name",)}


class FitmentSpecInline(StackedInline):
    model = FitmentSpec
    extra = 0
    max_num = 1


@admin.register(VehicleGeneration)
class VehicleGenerationAdmin(ModelAdmin):
    list_display = ("__str__", "year_from", "year_to")
    list_filter = ("model__make",)
    search_fields = ("name", "model__name", "model__make__name")
    list_select_related = ("model__make",)
    inlines = (FitmentSpecInline,)


@admin.register(UserVehicle)
class UserVehicleAdmin(ModelAdmin):
    list_display = ("user", "generation", "nickname", "is_default")
    search_fields = ("user__email",)
    autocomplete_fields = ("user", "generation")
