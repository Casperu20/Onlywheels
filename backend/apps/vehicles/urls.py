from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("my", views.UserVehicleViewSet, basename="user-vehicle")

urlpatterns = [
    path("makes/", views.MakeListView.as_view(), name="vehicle-makes"),
    path("models/", views.ModelListView.as_view(), name="vehicle-models"),
    path("generations/", views.GenerationListView.as_view(), name="vehicle-generations"),
    path(
        "generations/<uuid:pk>/",
        views.GenerationDetailView.as_view(),
        name="vehicle-generation-detail",
    ),
    *router.urls,
]
