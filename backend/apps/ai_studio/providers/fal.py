"""fal.ai: fast hosted Flux/SDXL endpoints (`fal_client.subscribe("fal-ai/flux/dev/image-to-image", ...)`)."""

from .base import GenerationRequest, GenerationResult, ImageProvider


class FalProvider(ImageProvider):
    name = "fal"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError("Phase 2")
