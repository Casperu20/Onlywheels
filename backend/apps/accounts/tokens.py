from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


def _cookie_kwargs(path: str) -> dict:
    return {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": path,
    }


def set_auth_cookies(response: Response, access: str, refresh: str | None = None) -> Response:
    jwt = settings.SIMPLE_JWT
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS,
        access,
        max_age=int(jwt["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        **_cookie_kwargs("/"),
    )
    if refresh:
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH,
            refresh,
            max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            **_cookie_kwargs(settings.AUTH_COOKIE_REFRESH_PATH),
        )
    return response


def login_response(response: Response, user) -> Response:
    refresh = RefreshToken.for_user(user)
    return set_auth_cookies(response, str(refresh.access_token), str(refresh))


def clear_auth_cookies(response: Response) -> Response:
    response.delete_cookie(
        settings.AUTH_COOKIE_ACCESS, path="/", samesite=settings.AUTH_COOKIE_SAMESITE
    )
    response.delete_cookie(
        settings.AUTH_COOKIE_REFRESH,
        path=settings.AUTH_COOKIE_REFRESH_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    return response
