from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import BrandViewSet, CarModel3DListView, CategoryViewSet, ProductViewSet

router = SimpleRouter()
router.register("brands", BrandViewSet, basename="brand")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")

urlpatterns = [path("car-models/", CarModel3DListView.as_view(), name="car-models")]
urlpatterns += router.urls
