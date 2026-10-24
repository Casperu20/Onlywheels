from django.contrib import admin, messages
from unfold.admin import ModelAdmin
from unfold.decorators import action

from . import services
from .models import Favorite, Review


@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__email", "product__name")
    list_select_related = ("user", "product__brand")


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("product", "rating", "title", "user", "is_verified_purchase", "status", "created_at")
    list_filter = ("status", "rating", "is_verified_purchase")
    search_fields = ("title", "body", "product__name", "user__email")
    list_select_related = ("product__brand", "user")
    readonly_fields = ("user", "product", "rating", "title", "body", "is_verified_purchase")
    actions = ("approve", "reject")

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        services.recalculate_rating(obj.product)

    @action(description="Approve selected reviews")
    def approve(self, request, queryset):
        reviews = list(queryset)
        for review in reviews:
            services.moderate(review, Review.Status.APPROVED)
        self.message_user(request, f"{len(reviews)} review(s) approved.", messages.SUCCESS)

    @action(description="Reject selected reviews")
    def reject(self, request, queryset):
        reviews = list(queryset)
        for review in reviews:
            services.moderate(review, Review.Status.REJECTED)
        self.message_user(request, f"{len(reviews)} review(s) rejected.", messages.SUCCESS)
