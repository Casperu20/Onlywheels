from rest_framework.routers import SimpleRouter

from apps.accounts import views

router = SimpleRouter()
router.register("addresses", views.AddressViewSet, basename="address")

urlpatterns = router.urls
