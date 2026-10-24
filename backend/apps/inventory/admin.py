from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm

from apps.catalog.models import ProductVariant

from .models import StockItem


class StockItemResource(resources.ModelResource):
    """CSV/Excel columns: sku, quantity (supplier stock import)."""

    sku = fields.Field(
        column_name="sku", attribute="variant", widget=ForeignKeyWidget(ProductVariant, field="sku")
    )

    class Meta:
        model = StockItem
        fields = ("sku", "quantity")
        import_id_fields = ("sku",)
        skip_unchanged = True


@admin.register(StockItem)
class StockItemAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_classes = (StockItemResource,)
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ("variant", "quantity", "reserved", "available")
    list_editable = ("quantity",)
    list_filter = ("variant__product__type", "variant__product__brand")
    search_fields = ("variant__sku", "variant__product__name")
    list_select_related = ("variant__product__brand",)
    autocomplete_fields = ("variant",)
    readonly_fields = ("reserved",)
