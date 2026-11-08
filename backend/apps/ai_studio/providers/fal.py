"""fal.ai image editing over plain HTTP (queue API).

Contract (docs: fal.ai/docs/api-reference/inference-api/queue): `Authorization: Key <FAL_KEY>`;
`POST https://queue.fal.run/<model>` with the model input as the JSON body returns `request_id`,
`status_url`, `response_url` and `cancel_url`; poll `status_url` until `COMPLETED`, then
`GET response_url` for `{"images": [{"url": ...}]}` or an error (`content_policy_violation` = 422).
The photo is sent as a base64 data URI (officially supported), `X-Fal-Store-IO: 0` keeps it out of
the request history and generated media expires after an hour. fal reports no per-request cost and
does not bill HTTP 5xx failures.
"""

import base64
import json
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

MEDIA_LIFETIME_SECONDS = 3600


class FalProvider(ImageProvider):
    name = "fal"

    def _headers(self, **extra) -> dict:
        return {"Authorization": f"Key {settings.FAL_KEY}", **extra}

    def check_configuration(self) -> None:
        if not settings.FAL_KEY:
            raise AIConfigurationError("FAL_KEY is required for AI_STUDIO_PROVIDER=fal.")
        if not settings.FAL_MODEL:
            raise AIConfigurationError("FAL_MODEL is required.")

    def estimate_cost(self) -> Decimal:
        return Decimal(settings.FAL_COST_PER_IMAGE_USD)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.check_configuration()
        if not request.image_bytes:
            raise AIProviderError("A photo is required.", charged=False)
        deadline = time.monotonic() + settings.AI_STUDIO_PROVIDER_TIMEOUT_SECONDS
        submitted = self._submit(request)
        request_id = submitted.get("request_id", "")
        base = f"{settings.FAL_QUEUE_BASE_URL.rstrip('/')}/{settings.FAL_MODEL.strip('/')}/requests/{request_id}"
        status_url = submitted.get("status_url") or f"{base}/status"
        response_url = submitted.get("response_url") or base
        cancel_url = submitted.get("cancel_url") or f"{base}/cancel"

        finished = poll_until(
            lambda: self._status(status_url),
            lambda value: value.get("status") == "COMPLETED",
            deadline=deadline,
        )
        if finished is None:
            try:
                requests.put(cancel_url, headers=self._headers(), timeout=15)
            except requests.RequestException:
                pass
            raise AIProviderError("fal request did not finish in time.", charged=None)

        payload = self._result(response_url)
        if any(payload.get("has_nsfw_concepts") or []):
            raise AIModerationError("fal flagged the result as NSFW.", charged=None)
        images = payload.get("images") or []
        url = images[0].get("url") if images and isinstance(images[0], dict) else None
        if not url:
            raise AIProviderError("fal returned no output image.", charged=True)
        image, content_type = download_image(url)
        return GenerationResult(image_bytes=image, content_type=content_type, cost=None, provider_job_id=request_id)

    def _submit(self, request: GenerationRequest) -> dict:
        data_uri = f"data:{request.image_content_type};base64,{base64.b64encode(request.image_bytes).decode()}"
        headers = self._headers(
            **{
                "X-Fal-Store-IO": "0",
                "X-Fal-Object-Lifecycle-Preference": json.dumps(
                    {"expiration_duration_seconds": MEDIA_LIFETIME_SECONDS}
                ),
            }
        )
        try:
            response = requests.post(
                f"{settings.FAL_QUEUE_BASE_URL.rstrip('/')}/{settings.FAL_MODEL.strip('/')}",
                headers=headers,
                json={"prompt": request.prompt, "image_url": data_uri},
                timeout=60,
            )
        except requests.ConnectionError as exc:
            raise AIProviderError(f"fal unreachable: {exc}", charged=False, retryable=True) from exc
        except requests.RequestException as exc:
            raise AIProviderError(f"fal submit failed: {exc}", charged=None) from exc
        self._raise_for_status(response)
        return response.json()

    def _status(self, url: str) -> dict:
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
        except requests.RequestException:
            return {}
        return response.json() if response.ok else {}

    def _result(self, url: str) -> dict:
        try:
            response = requests.get(url, headers=self._headers(), timeout=60)
        except requests.RequestException as exc:
            raise AIProviderError(f"fal result fetch failed: {exc}", charged=None) from exc
        self._raise_for_status(response)
        return response.json()

    def _raise_for_status(self, response) -> None:
        if response.ok:
            return
        message = f"fal HTTP {response.status_code}: {error_text(response)}"
        if response.status_code in (401, 403):
            raise AIConfigurationError(message)
        # fal never bills 5xx; a 422 may have consumed GPU time, so its charge is unknown.
        charged = False if response.status_code >= 500 or response.status_code in (400, 404, 429) else None
        if looks_like_moderation(message):
            raise AIModerationError(message, charged=charged)
        raise AIProviderError(message, charged=charged, retryable=response.status_code in (429, 503))
