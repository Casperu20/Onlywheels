import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture(autouse=True)
def _clear_cache():
    # Rate-limit counters live in the cache; keep tests independent.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(email="ana@example.com", password=PASSWORD, first_name="Ana")


@pytest.fixture
def auth_client(api_client: APIClient, user) -> APIClient:
    response = api_client.post(
        "/api/v1/auth/login/", {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    return api_client
