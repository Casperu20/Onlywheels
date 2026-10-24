from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.import_export.forms import ExportForm, ImportForm

from .models import Brand, Category, Product, ProductMedia, ProductVariant


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "product_type", "position")
    list_editable = ("position",)
    prepopulated_fields = {"slug": ("name",)}


class VariantInline(TabularInline):
    model = ProductVariant
    extra = 0
    fields = (
        "sku",
        "label",
        "price",
        "old_price",
        "finish",
        "diameter_in",
        "width_in",
        "et_mm",
        "pcd",
        "center_bore_mm",
        "tire_width_mm",
        "tire_aspect",
        "load_index",
        "speed_rating",
        "season",
        "thread_size",
        "is_active",
    )


class MediaInline(TabularInline):
    model = ProductMedia
    extra = 0


@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("name", "brand", "type", "is_active", "is_featured", "rating_avg")
    list_filter = ("type", "brand", "is_active", "is_featured")
    list_editable = ("is_active", "is_featured")
    search_fields = ("name", "brand__name", "variants__sku")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("brand",)
    readonly_fields = ("rating_avg", "rating_count")
    inlines = (VariantInline, MediaInline)


@admin.register(ProductVariant)
class ProductVariantAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ("sku", "product", "price", "old_price", "diameter_in", "pcd", "tire_size", "is_active")
    list_filter = ("product__type", "product__brand", "finish", "diameter_in", "is_active")
    list_editable = ("price", "old_price", "is_active")
    search_fields = ("sku", "product__name", "product__brand__name")
    list_select_related = ("product__brand",)
    autocomplete_fields = ("product",)
