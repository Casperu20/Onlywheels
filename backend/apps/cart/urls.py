from django.urls import path

from . import views

urlpatterns = [
    path("", views.CartView.as_view(), name="cart"),
    path("items/", views.CartItemsView.as_view(), name="cart-items"),
    path("items/<uuid:item_id>/", views.CartItemDetailView.as_view(), name="cart-item"),
    path("merge/", views.CartMergeView.as_view(), name="cart-merge"),
]
