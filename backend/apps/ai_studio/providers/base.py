import io
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

import requests
from PIL import Image


class AIProviderError(Exception):
    """Generation failed. `charged` says whether the provider may have billed the attempt."""

    def __init__(self, message: str, *, charged: bool | None = None, retryable: bool = False):
        super().__init__(message)
        self.charged = charged  # None = unknown
        self.retryable = retryable


class AIConfigurationError(AIProviderError):
    """Missing/invalid credentials or settings; nothing was sent to the provider."""

    def __init__(self, message: str):
        super().__init__(message, charged=False)


class AIModerationError(AIProviderError):
    """The provider refused the input or output (safety filter)."""


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    scene: str
    angle: str
    style: str
    image_bytes: bytes | None = None  # customer photo or 3D render (JPEG)
    image_content_type: str = "image/jpeg"


@dataclass(frozen=True)
class GenerationResult:
    image_bytes: bytes
    content_type: str
    cost: Decimal | None  # None = provider did not report it; the estimate is used
    provider_job_id: str = ""


class ImageProvider(ABC):
    """One adapter per AI vendor; chosen by settings.AI_STUDIO_PROVIDER."""

    name: str

    @abstractmethod
    def check_configuration(self) -> None:
        """Raise AIConfigurationError when credentials/settings are missing."""

    @abstractmethod
    def estimate_cost(self) -> Decimal:
        """Upper-bound USD cost of one generation, reserved from the daily budget."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult: ...


# --- Shared HTTP helpers --------------------------------------------------------------------------

MAX_RESULT_BYTES = 30 * 1024 * 1024
POLL_INTERVAL_SECONDS = 2
_FORMAT_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
_MODERATION_WORDS = ("nsfw", "sensitive", "safety", "content policy", "content_policy", "moderation", "flagged")


def looks_like_moderation(text: str) -> bool:
    lowered = (text or "").lower()
    return any(word in lowered for word in _MODERATION_WORDS)


def error_text(response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return (response.text or "")[:300]
    detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
    return str(detail)[:300]


def poll_until(fetch, is_done, *, deadline: float):
    """Call `fetch()` every few seconds until `is_done(value)`; return None if the deadline passes."""
    while True:
        value = fetch()
        if is_done(value):
            return value
        if time.monotonic() >= deadline:
            return None
        time.sleep(POLL_INTERVAL_SECONDS)


def download_image(url: str, *, headers: dict | None = None) -> tuple[bytes, str]:
    """Fetch a generated image and make sure it really is one (never trust the remote content type)."""
    try:
        response = requests.get(url, headers=headers or {}, timeout=60, stream=True)
    except requests.RequestException as exc:
        raise AIProviderError(f"Result download failed: {exc}", charged=True) from exc
    if not response.ok:
        raise AIProviderError(f"Result download returned HTTP {response.status_code}.", charged=True)
    chunks, size = [], 0
    for chunk in response.iter_content(chunk_size=65536):
        size += len(chunk)
        if size > MAX_RESULT_BYTES:
            raise AIProviderError("Result image is too large.", charged=True)
        chunks.append(chunk)
    content = b"".join(chunks)
    try:
        with Image.open(io.BytesIO(content)) as image:
            image_format = image.format
            image.verify()
    except Exception as exc:
        raise AIProviderError("Provider returned something that is not an image.", charged=True) from exc
    if image_format not in _FORMAT_TYPES:
        raise AIProviderError(f"Unsupported result format {image_format}.", charged=True)
    return content, _FORMAT_TYPES[image_format]
