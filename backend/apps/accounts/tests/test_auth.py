from unittest.mock import patch

import pytest
from django.conf import settings
from django.core import mail

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Passw0rd!"  # same as the `user` fixture in conftest.py
ACCESS = settings.AUTH_COOKIE_ACCESS
REFRESH = settings.AUTH_COOKIE_REFRESH


def test_register_creates_user_and_sets_httponly_cookies(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "Ion@Example.com", "password": PASSWORD, "first_name": "Ion"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["email"] == "ion@example.com"
    assert "password" not in response.json()
    assert response.cookies[ACCESS]["httponly"]
    assert response.cookies[REFRESH]["path"] == settings.AUTH_COOKIE_REFRESH_PATH
    assert User.objects.filter(email="ion@example.com").exists()


def test_register_rejects_duplicate_email_case_insensitive(api_client, user):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": user.email.upper(), "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert "email" in response.json()["error"]["fields"]


def test_register_rejects_weak_password(api_client):
    response = api_client.post(
        "/api/v1/auth/register/", {"email": "x@example.com", "password": "123"}, format="json"
    )

    assert response.status_code == 400
    assert "password" in response.json()["error"]["fields"]


def test_login_with_wrong_password_fails(api_client, user):
    response = api_client.post(
        "/api/v1/auth/login/", {"email": user.email, "password": "wrong"}, format="json"
    )

    assert response.status_code == 401
    assert ACCESS not in response.cookies


def test_me_requires_authentication(api_client):
    response = api_client.get("/api/v1/auth/me/")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_returns_and_updates_profile(auth_client):
    assert auth_client.get("/api/v1/auth/me/").json()["first_name"] == "Ana"

    response = auth_client.patch("/api/v1/auth/me/", {"phone": "0712345678"}, format="json")

    assert response.status_code == 200
    assert response.json()["phone"] == "0712345678"


def test_me_cannot_change_email(auth_client, user):
    auth_client.patch("/api/v1/auth/me/", {"email": "evil@example.com"}, format="json")

    user.refresh_from_db()
    assert user.email == "ana@example.com"


def test_bearer_header_works_for_native_clients(api_client, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    access = str(RefreshToken.for_user(user).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert api_client.get("/api/v1/auth/me/").status_code == 200


def test_refresh_rotates_tokens(auth_client):
    old_refresh = auth_client.cookies[REFRESH].value

    response = auth_client.post("/api/v1/auth/refresh/")

    assert response.status_code == 204
    assert response.cookies[REFRESH].value != old_refresh


def test_refresh_without_cookie_fails(api_client):
    assert api_client.post("/api/v1/auth/refresh/").status_code == 401


def test_logout_clears_cookies_and_blacklists_refresh(auth_client):
    old_refresh = auth_client.cookies[REFRESH].value

    response = auth_client.post("/api/v1/auth/logout/")

    assert response.status_code == 204
    assert response.cookies[ACCESS].value == ""
    auth_client.cookies[REFRESH] = old_refresh
    assert auth_client.post("/api/v1/auth/refresh/").status_code == 401


def test_password_change(auth_client, user):
    response = auth_client.post(
        "/api/v1/auth/password/change/",
        {"current_password": PASSWORD, "new_password": "An0ther-Str0ng!"},
        format="json",
    )

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.check_password("An0ther-Str0ng!")


def test_password_reset_flow(api_client, user, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            "/api/v1/auth/password/reset/", {"email": user.email}, format="json"
        )
    assert response.status_code == 204
    assert len(mail.outbox) == 1

    link = next(line for line in mail.outbox[0].body.splitlines() if "reset-password" in line)
    query = dict(part.split("=", 1) for part in link.split("?", 1)[1].split("&"))

    response = api_client.post(
        "/api/v1/auth/password/reset/confirm/",
        {"uid": query["uid"], "token": query["token"], "new_password": "Brand-N3w-Pass!"},
        format="json",
    )

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.check_password("Brand-N3w-Pass!")


def test_password_reset_unknown_email_does_not_leak(api_client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            "/api/v1/auth/password/reset/", {"email": "nobody@example.com"}, format="json"
        )

    assert response.status_code == 204
    assert len(mail.outbox) == 0


def test_password_reset_confirm_rejects_bad_token(api_client, user):
    response = api_client.post(
        "/api/v1/auth/password/reset/confirm/",
        {"uid": "bad", "token": "bad", "new_password": "Brand-N3w-Pass!"},
        format="json",
    )

    assert response.status_code == 400


def test_google_login_creates_and_links_user(api_client, user):
    info = {"sub": "google-123", "email": user.email, "email_verified": True}
    with patch("apps.accounts.services.verify_google_credential", return_value=info):
        response = api_client.post("/api/v1/auth/google/", {"credential": "x"}, format="json")

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.google_sub == "google-123"
    assert ACCESS in response.cookies


def test_google_login_rejected_when_not_configured(api_client, settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = ""
    response = api_client.post("/api/v1/auth/google/", {"credential": "x"}, format="json")

    assert response.status_code == 401


def test_csrf_is_enforced_with_json_error(user):
    from rest_framework.test import APIClient

    client = APIClient(enforce_csrf_checks=True)
    response = client.post("/api/v1/auth/login/", {"email": user.email, "password": PASSWORD}, format="json")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"

    client.get("/api/v1/csrf/")
    response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert response.status_code == 200

    # Cookie-authenticated requests also need the token.
    assert client.patch("/api/v1/auth/me/", {"phone": "0700000000"}, format="json").status_code == 403


def test_login_is_rate_limited(api_client, user):
    for _ in range(10):
        api_client.post("/api/v1/auth/login/", {"email": user.email, "password": "x"}, format="json")

    response = api_client.post(
        "/api/v1/auth/login/", {"email": user.email, "password": "x"}, format="json"
    )
    assert response.status_code == 429


def test_native_login_returns_user_and_token_pair(api_client, user):
    response = api_client.post(
        "/api/v1/auth/native/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == user.email
    assert "access" in data and "refresh" in data
    assert ACCESS not in response.cookies
    assert REFRESH not in response.cookies

    # Access token works as Bearer token without cookies or CSRF
    me = api_client.get(
        "/api/v1/auth/me/",
        HTTP_AUTHORIZATION=f"Bearer {data['access']}",
    )
    assert me.status_code == 200
    assert me.json()["email"] == user.email


def test_native_register_returns_token_pair_and_creates_session(api_client):
    response = api_client.post(
        "/api/v1/auth/native/register/",
        {"email": "native@example.com", "password": PASSWORD, "first_name": "Radu"},
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "native@example.com"
    assert data["user"]["first_name"] == "Radu"
    assert "access" in data and "refresh" in data
    assert ACCESS not in response.cookies
    assert REFRESH not in response.cookies

    me = api_client.get(
        "/api/v1/auth/me/",
        HTTP_AUTHORIZATION=f"Bearer {data['access']}",
    )
    assert me.status_code == 200
    assert me.json()["email"] == "native@example.com"


def test_native_refresh_rotates_and_rejects_reuse(api_client, user):
    login = api_client.post(
        "/api/v1/auth/native/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    ).json()

    old_refresh = login["refresh"]
    response = api_client.post(
        "/api/v1/auth/native/refresh/",
        {"refresh": old_refresh},
        format="json",
    )

    assert response.status_code == 200
    new_tokens = response.json()
    assert "access" in new_tokens and "refresh" in new_tokens
    assert new_tokens["refresh"] != old_refresh

    # New access token works
    me = api_client.get(
        "/api/v1/auth/me/",
        HTTP_AUTHORIZATION=f"Bearer {new_tokens['access']}",
    )
    assert me.status_code == 200

    # Old refresh token is blacklisted and cannot be reused
    reuse = api_client.post(
        "/api/v1/auth/native/refresh/",
        {"refresh": old_refresh},
        format="json",
    )
    assert reuse.status_code == 401


def test_native_logout_blacklists_refresh(api_client, user):
    login = api_client.post(
        "/api/v1/auth/native/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    ).json()

    refresh = login["refresh"]
    response = api_client.post(
        "/api/v1/auth/native/logout/",
        {"refresh": refresh},
        format="json",
    )
    assert response.status_code == 204

    # Refreshing with blacklisted token fails
    after_logout = api_client.post(
        "/api/v1/auth/native/refresh/",
        {"refresh": refresh},
        format="json",
    )
    assert after_logout.status_code == 401


def test_native_auth_does_not_change_cookie_login_contract(api_client, user):
    from rest_framework.test import APIClient

    # Web login requires CSRF and sets httpOnly cookies
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/v1/csrf/")
    response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert response.status_code == 200
    data = response.json()
    assert "access" not in data
    assert "refresh" not in data
    assert response.cookies[ACCESS]["httponly"]
    assert response.cookies[REFRESH]["httponly"]

    # Native login does NOT require CSRF token
    native_client = APIClient(enforce_csrf_checks=True)
    native_resp = native_client.post(
        "/api/v1/auth/native/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    assert native_resp.status_code == 200
    assert "access" in native_resp.json()


def test_native_refresh_rejects_deactivated_user(api_client, user):
    login = api_client.post(
        "/api/v1/auth/native/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    ).json()

    user.is_active = False
    user.save(update_fields=["is_active"])

    response = api_client.post(
        "/api/v1/auth/native/refresh/",
        {"refresh": login["refresh"]},
        format="json",
    )
    assert response.status_code == 401


def test_bearer_password_change_does_not_set_auth_cookies(api_client, user):
    login = api_client.post(
        "/api/v1/auth/native/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    ).json()

    response = api_client.post(
        "/api/v1/auth/password/change/",
        {"current_password": PASSWORD, "new_password": "An0ther-Str0ng!"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {login['access']}",
    )

    assert response.status_code == 204
    assert ACCESS not in response.cookies
    assert REFRESH not in response.cookies
