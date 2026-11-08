"""Replicate (replicate.com) image editing over plain HTTP.

Contract (docs: replicate.com/docs/reference/http): `Authorization: Bearer <REPLICATE_API_TOKEN>`;
the photo is uploaded privately with `POST /v1/files` (deleted again afterwards) and passed by URL;
`POST /v1/predictions {"version": "<owner>/<model>", "input": {...}}` with `Prefer: wait=N`, then
`GET urls.get` until succeeded/failed/canceled. Replicate removes API prediction inputs/outputs
after one hour. The API reports no per-request cost, so REPLICATE_COST_PER_IMAGE_USD is used.
"""

import time
from decimal import Decimal

import requests
from django.conf import settings

from .base import (
    AIConfigurationError,
    AIModerationError,
    AIProviderError,
    GenerationRequest,
    GenerationResult,
    ImageProvider,
    download_image,
    error_text,
    looks_like_moderation,
    poll_until,
)

TERMINAL = {"succeeded", "failed", "canceled"}


class ReplicateProvider(ImageProvider):
    name = "replicate"

    @property
    def base_url(self) -> str:
        return settings.REPLICATE_API_BASE_URL.rstrip("/")

    def _headers(self, **extra) -> dict:
        return {"Authorization": f"Bearer {settings.REPLICATE_API_TOKEN}", **extra}

    def check_configuration(self) -> None:
        if not settings.REPLICATE_API_TOKEN:
            raise AIConfigurationError("REPLICATE_API_TOKEN is required for AI_STUDIO_PROVIDER=replicate.")
        if not settings.REPLICATE_MODEL:
            raise AIConfigurationError("REPLICATE_MODEL is required.")

    def estimate_cost(self) -> Decimal:
        return Decimal(settings.REPLICATE_COST_PER_IMAGE_USD)

    def _input(self, request: GenerationRequest, image_url: str) -> dict:
        if "nano-banana" in settings.REPLICATE_MODEL:
            return {"prompt": request.prompt, "image_input": [image_url], "output_format": "jpg"}
        # FLUX Kontext family; 2 is the strictest safety level allowed with input images.
        return {"prompt": request.prompt, "input_image": image_url, "output_format": "jpg", "safety_tolerance": 2}

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.check_configuration()
        if not request.image_bytes:
            raise AIProviderError("A photo is required.", charged=False)
        uploaded = self._upload(request)
        try:
            return self._predict(request, uploaded["urls"]["get"])
        finally:
            self._delete_file(uploaded["id"])

    def _upload(self, request: GenerationRequest) -> dict:
        try:
            response = requests.post(
                f"{self.base_url}/files",
                headers=self._headers(),
                files={"content": ("photo.jpg", request.image_bytes, request.image_content_type)},
                timeout=60,
            )
        except requests.RequestException as exc:
            raise AIProviderError(f"Replicate upload failed: {exc}", charged=False, retryable=True) from exc
        self._raise_for_status(response, charged=False)
        payload = response.json()
        if not payload.get("id") or not (payload.get("urls") or {}).get("get"):
            raise AIProviderError("Replicate upload returned no file URL.", charged=False)
        return payload

    def _delete_file(self, file_id: str) -> None:
        try:
            requests.delete(f"{self.base_url}/files/{file_id}", headers=self._headers(), timeout=15)
        except requests.RequestException:
            pass  # Replicate expires it anyway; never fail a finished job over cleanup.

    def _predict(self, request: GenerationRequest, image_url: str) -> GenerationResult:
        timeout = settings.AI_STUDIO_PROVIDER_TIMEOUT_SECONDS
        deadline = time.monotonic() + timeout
        wait = max(1, min(60, timeout))
        try:
            response = requests.post(
                f"{self.base_url}/predictions",
                headers=self._headers(Prefer=f"wait={wait}", **{"Cancel-After": f"{max(timeout, 5)}s"}),
                json={"version": settings.REPLICATE_MODEL, "input": self._input(request, image_url)},
                timeout=wait + 15,
            )
        except requests.ConnectionError as exc:
            raise AIProviderError(f"Replicate unreachable: {exc}", charged=False, retryable=True) from exc
        except requests.RequestException as exc:
            # The prediction may have been created; we cannot tell, so assume it was billed.
            raise AIProviderError(f"Replicate prediction request failed: {exc}", charged=None) from exc
        self._raise_for_status(response, charged=None if response.status_code >= 500 else False)
        prediction = response.json()

        if prediction.get("status") not in TERMINAL:
            get_url = (prediction.get("urls") or {}).get("get") or f"{self.base_url}/predictions/{prediction['id']}"
            prediction = poll_until(
                lambda: self._get_prediction(get_url),
                lambda value: value.get("status") in TERMINAL,
                deadline=deadline,
            ) or self._cancel(prediction)

        status = prediction.get("status")
        job_id = prediction.get("id", "")
        if status == "failed":
            message = str(prediction.get("error") or "Replicate prediction failed.")
            if looks_like_moderation(message):
                raise AIModerationError(message, charged=None)
            raise AIProviderError(message, charged=None)
        if status != "succeeded":
            raise AIProviderError(f"Replicate prediction {status or 'unknown'}.", charged=None)

        output = prediction.get("output")
        url = output[0] if isinstance(output, list) and output else output
        if not isinstance(url, str) or not url:
            raise AIProviderError("Replicate returned no output image.", charged=True)
        image, content_type = download_image(url)
        return GenerationResult(image_bytes=image, content_type=content_type, cost=None, provider_job_id=job_id)

    def _get_prediction(self, url: str) -> dict:
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
        except requests.RequestException:
            return {}  # transient; keep polling until the deadline
        return response.json() if response.ok else {}

    def _cancel(self, prediction: dict) -> dict:
        cancel_url = (prediction.get("urls") or {}).get("cancel")
        if cancel_url:
            try:
                requests.post(cancel_url, headers=self._headers(), timeout=15)
            except requests.RequestException:
                pass
        return {"id": prediction.get("id", ""), "status": "timed out"}

    def _raise_for_status(self, response, *, charged: bool | None) -> None:
        if response.ok:
            return
        message = f"Replicate HTTP {response.status_code}: {error_text(response)}"
        if response.status_code in (401, 402, 403):
            raise AIConfigurationError(message)
        if looks_like_moderation(message):
            raise AIModerationError(message, charged=charged)
        raise AIProviderError(message, charged=charged, retryable=response.status_code in (429, 503))
