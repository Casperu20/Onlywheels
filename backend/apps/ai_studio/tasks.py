import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .models import AIGeneration
from .options import build_prompt
from .providers import (
    AIConfigurationError,
    AIModerationError,
    AIProviderError,
    GenerationRequest,
    get_image_provider,
)
from .services import delete_images, purge_generations, settle_budget

logger = logging.getLogger(__name__)

EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
STUCK_AFTER = timedelta(minutes=30)

MESSAGES = {
    "moderation": "The AI provider's safety filter rejected this photo or result. Try a different photo.",
    "unavailable": "The AI studio is not available right now. You can retry later.",
    "failed": "The image could not be generated. You can retry it.",
}


@shared_task(soft_time_limit=240, time_limit=300)
def generate_image_task(generation_id: str) -> None:
    with transaction.atomic():
        generation = (
            AIGeneration.objects.select_for_update(of=("self",))
            .select_related("variant__product__brand")
            .filter(pk=generation_id)
            .first()
        )
        if generation is None or generation.status != AIGeneration.Status.QUEUED or generation.deleted_at:
            return
        generation.status = AIGeneration.Status.RUNNING
        generation.started_at = timezone.now()
        generation.save(update_fields=["status", "started_at", "updated_at"])

    try:
        provider = get_image_provider(generation.provider)
        if provider is None:
            raise AIConfigurationError("AI studio provider disabled after the job was queued.")
        provider.check_configuration()
        with generation.input_image.open("rb") as stored:
            image = stored.read()
        result = provider.generate(
            GenerationRequest(
                prompt=build_prompt(generation),
                scene=generation.scene,
                angle=generation.angle,
                style=generation.style,
                image_bytes=image,
            )
        )
    except AIProviderError as exc:
        _fail(generation_id, exc, exc.charged)
        return
    except Exception as exc:  # network bugs, unexpected payloads, soft time limit
        logger.exception("AI generation %s crashed", generation_id)
        _fail(generation_id, exc, None)
        return

    with transaction.atomic():
        generation = AIGeneration.objects.select_for_update().get(pk=generation_id)
        cost = result.cost if result.cost is not None else generation.estimated_cost
        generation.cost = cost
        generation.provider_job_id = result.provider_job_id[:120]
        generation.finished_at = timezone.now()
        if generation.status == AIGeneration.Status.RUNNING and not generation.deleted_at:
            extension = EXTENSIONS.get(result.content_type, "png")
            generation.result_image.save(f"result.{extension}", ContentFile(result.image_bytes), save=False)
            generation.status = AIGeneration.Status.DONE
        # else: the owner deleted it meanwhile; the provider still charged us, the image is discarded.
        generation.save()
        settle_budget(generation, cost)


def _fail(generation_id, exc: Exception, charged: bool | None) -> None:
    if isinstance(exc, AIModerationError):
        message = MESSAGES["moderation"]
    elif isinstance(exc, AIConfigurationError):
        message = MESSAGES["unavailable"]
    else:
        message = MESSAGES["failed"]
    with transaction.atomic():
        generation = AIGeneration.objects.select_for_update().get(pk=generation_id)
        if generation.status == AIGeneration.Status.RUNNING:
            generation.status = AIGeneration.Status.FAILED
            generation.error = message
        generation.error_detail = f"{type(exc).__name__}: {exc}"[:2000]
        generation.finished_at = timezone.now()
        generation.save()
        # Unknown charge: keep the estimate as spent so the daily ceiling stays conservative.
        settle_budget(generation, Decimal("0") if charged is False else generation.estimated_cost)


@shared_task
def cleanup_expired_generations() -> dict:
    """Retention: delete images and rows after AI_STUDIO_RETENTION_DAYS; recover stuck jobs."""
    now = timezone.now()
    stuck = AIGeneration.objects.filter(status=AIGeneration.Status.RUNNING, started_at__lt=now - STUCK_AFTER)
    recovered = 0
    for generation in stuck:
        _fail(generation.pk, TimeoutError("Worker did not finish the job."), None)
        recovered += 1

    expired = AIGeneration.objects.filter(created_at__lt=now - timedelta(days=settings.AI_STUDIO_RETENTION_DAYS))
    purged = purge_generations(expired)

    # Images of jobs deleted by the owner are already gone; nothing else to do for them.
    for generation in AIGeneration.objects.filter(deleted_at__isnull=False).exclude(input_image="", result_image=""):
        delete_images(generation)
        generation.save(update_fields=["input_image", "result_image"])
    return {"recovered": recovered, "purged": purged}
