"""AI photo studio: quotas, the global daily budget and the generation lifecycle.

1. `POST /api/v1/ai/generations/` validates and normalises the photo, then `reserve_generation`
   reserves the provider's cost estimate from today's `AIDailyBudget` (row locked), checks the
   per-user daily limit, stores the photo privately and queues `generate_image_task` (HTTP 202).
2. The task calls the configured provider (`providers/`) and either stores the result or records a
   customer-safe error; `settle_budget` then moves the reservation to spent.
3. The client polls `GET /api/v1/ai/generations/{id}/`; images are streamed to the owner only.
4. `cleanup_expired_generations` deletes images after AI_STUDIO_RETENTION_DAYS.
"""

import logging
from datetime import datetime, time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from .models import AIDailyBudget, AIGeneration
from .providers import AIConfigurationError, get_image_provider

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = (AIGeneration.Status.QUEUED, AIGeneration.Status.RUNNING)


class AIStudioUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The AI studio is not available right now. Please try again later."
    default_code = "ai_studio_unavailable"


class AILimitReached(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "You have used all your AI generations for today. Come back tomorrow."
    default_code = "ai_daily_limit"


class AIBudgetExhausted(AILimitReached):
    default_detail = "The AI studio has reached its usage limit for today. Please try again tomorrow."
    default_code = "ai_daily_budget"


def today():
    return timezone.localdate()


def start_of_today() -> datetime:
    return timezone.make_aware(datetime.combine(today(), time.min))


def today_budget(day=None) -> AIDailyBudget:
    budget, _ = AIDailyBudget.objects.get_or_create(day=day or today())
    return budget


def used_today(user) -> int:
    """Jobs created since local midnight; failed ones are given back (they produced nothing)."""
    return (
        AIGeneration.objects.filter(user=user, created_at__gte=start_of_today())
        .exclude(status=AIGeneration.Status.FAILED)
        .count()
    )


def remaining_quota(user) -> int:
    return max(settings.AI_STUDIO_DAILY_QUOTA - used_today(user), 0)


def configured_provider():
    """The provider if the studio is enabled and configured; otherwise None (reason logged)."""
    try:
        provider = get_image_provider()
        if provider is not None:
            provider.check_configuration()
        return provider
    except AIConfigurationError as exc:
        logger.warning("AI studio misconfigured: %s", exc)
        return None


def reserve_generation(
    user,
    *,
    image: bytes,
    scene: str,
    style: str,
    variant=None,
    source: str = AIGeneration.Source.USER_PHOTO,
) -> AIGeneration:
    provider = configured_provider()
    if provider is None:
        raise AIStudioUnavailable()
    estimate = Decimal(provider.estimate_cost()).quantize(Decimal("0.0001"))
    day = today()

    with transaction.atomic():
        # Serialise one user's requests so two parallel uploads cannot both take the last slot.
        get_user_model().objects.select_for_update().filter(pk=user.pk).first()
        if remaining_quota(user) <= 0:
            raise AILimitReached()
        today_budget(day)
        budget = AIDailyBudget.objects.select_for_update().get(day=day)
        if budget.spent_usd + budget.reserved_usd + estimate > settings.AI_STUDIO_DAILY_BUDGET_USD:
            raise AIBudgetExhausted()
        budget.reserved_usd += estimate
        budget.save(update_fields=["reserved_usd"])

        generation = AIGeneration(
            user=user,
            variant=variant,
            provider=provider.name,
            source=source,
            scene=scene,
            style=style,
            estimated_cost=estimate,
            budget_day=day,
        )
        generation.input_image.save("input.jpg", ContentFile(image), save=False)
        generation.save()
        transaction.on_commit(lambda: _enqueue(generation.pk))
    return generation


def _enqueue(generation_id) -> None:
    from .tasks import generate_image_task

    generate_image_task.delay(str(generation_id))


def retry_generation(generation: AIGeneration) -> AIGeneration:
    if generation.status != AIGeneration.Status.FAILED or not generation.input_image:
        raise ValidationError({"detail": "Only failed generations with their photo can be retried."})
    with generation.input_image.open("rb") as stored:
        image = stored.read()
    return reserve_generation(
        generation.user,
        image=image,
        scene=generation.scene,
        style=generation.style,
        variant=generation.variant,
        source=generation.source,
    )


def settle_budget(generation: AIGeneration, spent: Decimal) -> None:
    """Release the reservation and record what was (or may have been) charged. Idempotent."""
    if generation.budget_settled:
        return
    if generation.budget_day:
        budget = AIDailyBudget.objects.select_for_update().filter(day=generation.budget_day).first()
        if budget is not None:
            budget.reserved_usd = max(budget.reserved_usd - generation.estimated_cost, Decimal("0"))
            budget.spent_usd += spent
            budget.save(update_fields=["reserved_usd", "spent_usd"])
    generation.budget_settled = True
    generation.save(update_fields=["budget_settled", "updated_at"])


def delete_images(generation: AIGeneration) -> None:
    """Remove storage objects first; the row only forgets them once they are gone."""
    for field in (generation.input_image, generation.result_image):
        if field:
            field.delete(save=False)


@transaction.atomic
def delete_generation(generation: AIGeneration) -> None:
    generation = AIGeneration.objects.select_for_update().get(pk=generation.pk)
    delete_images(generation)
    if generation.status == AIGeneration.Status.QUEUED:
        # Never sent to the provider: give the reservation back.
        generation.status = AIGeneration.Status.CANCELLED
        generation.save(update_fields=["status"])
        settle_budget(generation, Decimal("0"))
    elif generation.status == AIGeneration.Status.RUNNING:
        # The provider may already be working; the task settles the budget and discards the result.
        generation.status = AIGeneration.Status.CANCELLED
    generation.deleted_at = timezone.now()
    generation.save(update_fields=["status", "input_image", "result_image", "deleted_at", "updated_at"])


@transaction.atomic
def purge_generations(queryset) -> int:
    """Hard-delete generations (GDPR erasure, retention). Images go first, then the rows."""
    count = 0
    for generation in queryset.select_for_update():
        delete_images(generation)
        if not generation.budget_settled and generation.status == AIGeneration.Status.QUEUED:
            settle_budget(generation, Decimal("0"))
        elif not generation.budget_settled:
            settle_budget(generation, generation.estimated_cost)
        generation.delete()
        count += 1
    return count


def export_generations(user) -> list[dict]:
    return list(
        user.ai_generations.values(
            "id", "created_at", "status", "provider", "source", "scene", "style", "variant__sku", "deleted_at"
        )
    )
