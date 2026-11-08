import logging

from celery import shared_task

from . import wheelsize

logger = logging.getLogger(__name__)


@shared_task
def sync_makes_task() -> None:
    logger.info("Executing background sync for vehicle makes")
    wheelsize.ensure_makes(force=True)


@shared_task
def sync_models_task(make_id: str) -> None:
    logger.info("Executing background sync for models of make %s", make_id)
    wheelsize.ensure_models(make_id, force=True)


@shared_task
def sync_generations_task(model_id: str) -> None:
    logger.info("Executing background sync for generations of model %s", model_id)
    wheelsize.ensure_generations(model_id, force=True)


@shared_task
def sync_fitment_task(generation_id: str) -> None:
    logger.info("Executing background sync for fitment of generation %s", generation_id)
    wheelsize.ensure_fitment(generation_id, force=True)
