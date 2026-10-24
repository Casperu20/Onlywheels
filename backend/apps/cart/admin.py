from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Cart, CartItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("variant",)


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__email",)
    inlines = (CartItemInline,)
