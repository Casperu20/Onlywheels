from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    scene: str
    angle: str
    style: str
    image_url: str | None = None  # customer photo or 3D render
    mask_url: str | None = None  # wheel area for inpainting


@dataclass(frozen=True)
class GenerationResult:
    image_bytes: bytes
    cost: float


class ImageProvider(ABC):
    """One adapter per AI vendor; chosen by settings.AI_STUDIO_PROVIDER."""

    name: str

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult: ...
