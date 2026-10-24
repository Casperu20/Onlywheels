from django.urls import path

from apps.reviews.views import FavoriteDetailView, FavoriteListView

urlpatterns = [
    path("", FavoriteListView.as_view(), name="favorites"),
    path("<uuid:product_id>/", FavoriteDetailView.as_view(), name="favorite-detail"),
]
