from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_v1 = [
    path("", include("apps.core.urls")),
    path("auth/", include("apps.accounts.urls.auth")),
    path("accounts/", include("apps.accounts.urls.accounts")),
    path("vehicles/", include("apps.vehicles.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("favorites/", include("apps.reviews.urls.favorites")),
    path("reviews/", include("apps.reviews.urls.reviews")),
    path("cart/", include("apps.cart.urls")),
    path("garages/", include("apps.garages.urls")),
    path("", include("apps.orders.urls")),
    path("payments/", include("apps.payments.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
