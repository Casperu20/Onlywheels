from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .models import Address
from .serializers import (
    AddressSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .tokens import clear_auth_cookies, login_response, set_auth_cookies


@method_decorator(csrf_protect, name="dispatch")
class PublicAuthView(APIView):
    """Endpoints used before the user is logged in: no auth, CSRF checked, rate limited."""

    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth"


def _logged_in(user, response_status=status.HTTP_200_OK) -> Response:
    update_last_login(None, user)
    response = Response(UserSerializer(user).data, status=response_status)
    return login_response(response, user)


@extend_schema(tags=["auth"])
class RegisterView(PublicAuthView):
    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(**serializer.validated_data)
        return _logged_in(user, status.HTTP_201_CREATED)


@extend_schema(tags=["auth"])
class LoginView(PublicAuthView):
    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise AuthenticationFailed("Invalid email or password.")
        return _logged_in(user)


@extend_schema(tags=["auth"])
class GoogleLoginView(PublicAuthView):
    @extend_schema(request=GoogleLoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        info = services.verify_google_credential(serializer.validated_data["credential"])
        user = services.get_or_create_google_user(info)
        return _logged_in(user)


@method_decorator(csrf_protect, name="dispatch")
@extend_schema(tags=["auth"])
class RefreshView(APIView):
    """Rotates the refresh cookie and issues a new access cookie."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if not token:
            raise AuthenticationFailed("Not logged in.")
        serializer = TokenRefreshSerializer(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return set_auth_cookies(
            response, serializer.validated_data["access"], serializer.validated_data.get("refresh")
        )


@method_decorator(csrf_protect, name="dispatch")
@extend_schema(tags=["auth"])
class LogoutView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass
        return clear_auth_cookies(Response(status=status.HTTP_204_NO_CONTENT))


@extend_schema(tags=["auth"])
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ["get", "patch", "options"]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["auth"])
class PasswordChangeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(request=PasswordChangeSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return login_response(Response(status=status.HTTP_204_NO_CONTENT), request.user)


@extend_schema(tags=["auth"])
class PasswordResetRequestView(PublicAuthView):
    @extend_schema(request=PasswordResetRequestSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["auth"])
class PasswordResetConfirmView(PublicAuthView):
    @extend_schema(request=PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reset_password(**serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["accounts"])
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Address.objects.none()
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
