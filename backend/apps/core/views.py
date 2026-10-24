from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        responses=inline_serializer("Health", {"status": serializers.CharField()}),
        tags=["core"],
    )
    def get(self, request):
        return Response({"status": "ok"})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Sets the `csrftoken` cookie. The SPA calls this once on startup."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(responses={204: None}, tags=["core"])
    def get(self, request):
        return Response(status=204)
