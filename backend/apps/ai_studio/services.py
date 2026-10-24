"""
AI photo studio (phase 2) – external image APIs only, no self-hosted models.

Planned flow (see docs/architecture/ARCHITECTURE.md §7.3):
1. `POST /api/v1/ai/generations/` with scene, angle, style, variant_id and optionally a photo
   (uploaded directly to S3 via a pre-signed URL). `request_generation` checks the daily quota,
   creates an `AIGeneration` (queued) and enqueues `generate_image_task` → HTTP 202 {id}.
2. The Celery task builds the prompt (car + wheel description + scene), calls the configured
   provider (`providers/`), uploads the result to storage and sets status=done (or failed with
   `error`). Retries with backoff on provider timeouts; hard time limit ~120 s.
3. The client polls `GET /api/v1/ai/generations/{id}/` (WebSocket via Django Channels later).
4. Cost control: `AI_STUDIO_DAILY_QUOTA` per user, `cost` stored per generation, admin overview.
5. Safety: provider moderation flags are stored in `error`; API keys live only in env vars.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import Throttled

from .models import AIGeneration


def remaining_quota(user) -> int:
    since = timezone.now() - timedelta(days=1)
    used = AIGeneration.objects.filter(user=user, created_at__gte=since).exclude(
        status=AIGeneration.Status.FAILED
    ).count()
    return max(settings.AI_STUDIO_DAILY_QUOTA - used, 0)


def request_generation(user, **params) -> AIGeneration:
    if remaining_quota(user) <= 0:
        raise Throttled(detail="Daily AI generation limit reached.")
    raise NotImplementedError("AI studio is planned for phase 2 (see module docstring).")
