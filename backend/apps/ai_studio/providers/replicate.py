"""Replicate (replicate.com): SDXL/Flux + ControlNet/inpainting models via `replicate.run(...)`."""

from .base import GenerationRequest, GenerationResult, ImageProvider


class ReplicateProvider(ImageProvider):
    name = "replicate"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError("Phase 2")
