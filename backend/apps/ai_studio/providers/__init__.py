from django.conf import settings

from .base import (
    AIConfigurationError,
    AIModerationError,
    AIProviderError,
    GenerationRequest,
    GenerationResult,
    ImageProvider,
)

__all__ = [
    "AIConfigurationError",
    "AIModerationError",
    "AIProviderError",
    "GenerationRequest",
    "GenerationResult",
    "ImageProvider",
    "get_image_provider",
]


def get_image_provider(name: str | None = None) -> ImageProvider | None:
    """The configured provider, or None when the studio is disabled (empty AI_STUDIO_PROVIDER)."""
    name = (settings.AI_STUDIO_PROVIDER if name is None else name).strip().lower()
    if not name:
        return None
    if name == "replicate":
        from .replicate import ReplicateProvider

        return ReplicateProvider()
    if name == "fal":
        from .fal import FalProvider

        return FalProvider()
    raise AIConfigurationError(f"Unknown AI_STUDIO_PROVIDER {name!r}; use 'replicate' or 'fal'.")
