from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import GenerationViewSet, StudioInfoView

router = SimpleRouter()
router.register("generations", GenerationViewSet, basename="ai-generation")

urlpatterns = [
    path("studio/", StudioInfoView.as_view(), name="ai-studio"),
    *router.urls,
]
