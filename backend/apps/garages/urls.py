from rest_framework.routers import SimpleRouter

from .views import GarageViewSet

router = SimpleRouter()
router.register("", GarageViewSet, basename="garage")

urlpatterns = router.urls
