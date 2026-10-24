from rest_framework.routers import SimpleRouter

from .views import BrandViewSet, CategoryViewSet, ProductViewSet

router = SimpleRouter()
router.register("brands", BrandViewSet, basename="brand")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")

urlpatterns = router.urls
