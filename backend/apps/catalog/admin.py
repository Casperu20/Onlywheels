from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.import_export.forms import ExportForm, ImportForm

from .car_model_detection import detect_wheel_anchors
from .models import Brand, CarModel3D, Category, Model3D, Product, ProductMedia, ProductVariant


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
        "shipping_weight_kg",
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


class Model3DInline(StackedInline):
    model = Model3D
    extra = 0
    max_num = 1


@admin.register(CarModel3D)
class CarModel3DAdmin(ModelAdmin):
    list_display = ("name", "body_type", "is_active", "detection_status", "sort_order")
    list_filter = ("body_type", "is_active", "detection_status")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name", "slug", "vehicle_model__name", "vehicle_model__make__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("vehicle_model",)
    readonly_fields = (
        "detected_anchors",
        "detection_status",
        "detection_message",
        "effective_anchors_display",
        "preview_link",
    )
    fields = (
        "name",
        "slug",
        "body_type",
        "glb_file",
        "length_m",
        "front",
        "vehicle_model",
        "wheel_anchors",
        "detected_anchors",
        "detection_status",
        "detection_message",
        "effective_anchors_display",
        "attribution",
        "source_url",
        "is_active",
        "sort_order",
        "preview_link",
    )

    def save_model(self, request, obj: CarModel3D, form, change: bool) -> None:
        detect = not change or "glb_file" in form.changed_data
        super().save_model(request, obj, form, change)
        if detect:
            with obj.glb_file.open("rb") as glb_file:
                result = detect_wheel_anchors(glb_file)
            obj.detected_anchors = result.anchors
            obj.detection_status = (
                CarModel3D.DetectionStatus.OK if result.anchors else CarModel3D.DetectionStatus.FAILED
            )
            obj.detection_message = result.error or ""
            obj.save(update_fields=("detected_anchors", "detection_status", "detection_message", "updated_at"))

    @admin.display(description="Effective wheel positions")
    def effective_anchors_display(self, obj: CarModel3D) -> str:
        return str(obj.effective_wheel_anchors or "Not detected; enter manual wheel positions.")

    @admin.display(description="Showroom preview")
    def preview_link(self, obj: CarModel3D) -> str:
        if not obj.pk or not obj.is_active or not obj.is_usable:
            return "Available after activation and successful wheel detection."
        return format_html(
            '<a href="{}/showroom?view=car&amp;car={}" target="_blank" rel="noopener">Preview in showroom</a>',
            settings.FRONTEND_URL.rstrip("/"),
            obj.slug,
        )


@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("name", "brand", "type", "is_active", "is_featured", "rating_avg")
    list_filter = ("type", "brand", "is_active", "is_featured")
    list_editable = ("is_active", "is_featured")
    search_fields = ("name", "brand__name", "variants__sku")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("brand",)
    readonly_fields = ("rating_avg", "rating_count")
    inlines = (VariantInline, MediaInline, Model3DInline)


@admin.register(ProductVariant)
class ProductVariantAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = (
        "sku",
        "product",
        "price",
        "old_price",
        "shipping_weight_kg",
        "diameter_in",
        "pcd",
        "tire_size",
        "is_active",
    )
    list_filter = ("product__type", "product__brand", "finish", "diameter_in", "is_active")
    list_editable = ("price", "old_price", "shipping_weight_kg", "is_active")
    search_fields = ("sku", "product__name", "product__brand__name")
    list_select_related = ("product__brand",)
    autocomplete_fields = ("product",)
