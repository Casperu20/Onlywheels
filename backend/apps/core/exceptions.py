from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def _first_message(value) -> str:
    if isinstance(value, dict):
        value = next(iter(value.values()), "")
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict | list):
        return _first_message(value)
    return str(value)


def api_exception_handler(exc, context):
    """Wrap every API error as {"error": {"code", "message", "fields"?}} (see docs/api/CONVENTIONS.md)."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        data = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
        response.data = {
            "error": {
                "code": "validation_error",
                "message": _first_message(data),
                "fields": data,
            }
        }
        return response

    if isinstance(exc, Http404):
        code = "not_found"
    elif isinstance(exc, DjangoPermissionDenied):
        code = "permission_denied"
    else:
        code = getattr(exc, "default_code", "error")

    detail = response.data.get("detail", response.data) if isinstance(response.data, dict) else response.data
    response.data = {"error": {"code": code, "message": str(detail)}}
    return response
