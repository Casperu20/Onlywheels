import io
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.test import Client
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.ai_studio.models import AIGeneration
from apps.ai_studio.providers import AIModerationError, AIProviderError, GenerationResult
from apps.ai_studio.services import delete_generation, remaining_quota, reserve_generation, today_budget
from apps.ai_studio.tasks import cleanup_expired_generations, generate_image_task
from apps.catalog.models import ProductType
from tests.factories import make_product, make_variant

pytestmark = pytest.mark.django_db

ESTIMATE = Decimal("0.0400")


def jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), "red").save(buffer, format="JPEG")
    return buffer.getvalue()


def png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def provider(settings, tmp_path):
    settings.AI_STUDIO_PROVIDER = "replicate"
    settings.AI_STUDIO_PRIVATE_ROOT = str(tmp_path)
    fake = Mock()
    fake.name = "replicate"
    fake.estimate_cost.return_value = ESTIMATE
    fake.generate.return_value = GenerationResult(png(), "image/png", None, "pred-1")
    with (
        patch("apps.ai_studio.services.get_image_provider", return_value=fake),
        patch("apps.ai_studio.tasks.get_image_provider", return_value=fake),
    ):
        yield fake


def queued(user, **fields) -> AIGeneration:
    # on_commit callbacks do not run inside the test transaction, so the job stays queued.
    return reserve_generation(user, image=jpeg(), scene="city_night", style="photo", **fields)


def test_successful_generation_stores_private_result_and_settles_budget(provider, user, tmp_path):
    variant = make_variant(make_product(type=ProductType.WHEEL, name="CH-R"))
    generation = queued(user, variant=variant)

    generate_image_task(str(generation.pk))

    generation.refresh_from_db()
    assert generation.status == "done"
    assert generation.provider_job_id == "pred-1"
    assert generation.cost == ESTIMATE  # provider reported no cost
    assert str(tmp_path) in generation.result_image.path
    assert generation.result_image.name.endswith(".png")
    request = provider.generate.call_args.args[0]
    assert "CH-R" in request.prompt and "city street at night" in request.prompt
    assert request.image_bytes.startswith(b"\xff\xd8")
    budget = today_budget()
    assert (budget.reserved_usd, budget.spent_usd) == (Decimal("0"), ESTIMATE)


def test_queued_job_runs_when_the_transaction_commits(provider, user, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        generation = queued(user)
    generation.refresh_from_db()
    assert generation.status == "done"


def test_moderation_failure_is_customer_safe_and_keeps_estimate_as_spent(provider, user):
    provider.generate.side_effect = AIModerationError("NSFW flagged by model xyz", charged=None)
    generation = queued(user)

    generate_image_task(str(generation.pk))

    generation.refresh_from_db()
    assert generation.status == "failed"
    assert "safety filter" in generation.error
    assert "xyz" not in generation.error
    assert "xyz" in generation.error_detail
    assert today_budget().spent_usd == ESTIMATE
    assert today_budget().reserved_usd == Decimal("0")


def test_uncharged_failure_returns_budget_and_quota(provider, user, settings):
    provider.generate.side_effect = AIProviderError("HTTP 500", charged=False)
    generation = queued(user)

    generate_image_task(str(generation.pk))

    generation.refresh_from_db()
    assert generation.status == "failed"
    assert (today_budget().reserved_usd, today_budget().spent_usd) == (Decimal("0"), Decimal("0"))
    assert remaining_quota(user) == settings.AI_STUDIO_DAILY_QUOTA


def test_unexpected_crash_fails_the_job(provider, user):
    provider.generate.side_effect = KeyError("output")
    generation = queued(user)
    generate_image_task(str(generation.pk))
    generation.refresh_from_db()
    assert generation.status == "failed"
    assert generation.error
    assert today_budget().spent_usd == ESTIMATE


def test_job_deleted_before_it_runs_is_skipped(provider, user):
    generation = queued(user)
    delete_generation(generation)
    generate_image_task(str(generation.pk))
    provider.generate.assert_not_called()
    generate_image_task("00000000-0000-0000-0000-000000000000")


def test_job_deleted_while_running_discards_the_result_but_pays(provider, user):
    generation = queued(user)

    def delete_mid_flight(request):
        delete_generation(AIGeneration.objects.get(pk=generation.pk))
        return GenerationResult(png(), "image/png", Decimal("0.039"), "pred-2")

    provider.generate.side_effect = delete_mid_flight
    generate_image_task(str(generation.pk))

    generation.refresh_from_db()
    assert generation.status == "cancelled"
    assert not generation.result_image
    assert today_budget().spent_usd == Decimal("0.039")
    assert today_budget().reserved_usd == Decimal("0")


def test_result_streams_to_the_owner(provider, user):
    generation = queued(user)
    generate_image_task(str(generation.pk))
    client = APIClient()
    client.force_authenticate(user)
    response = client.get(f"/api/v1/ai/generations/{generation.pk}/result/")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    body = client.get(f"/api/v1/ai/generations/{generation.pk}/").json()
    assert body["status"] == "done"
    assert body["result_url"].endswith("/result/")


def test_cleanup_purges_expired_jobs_and_recovers_stuck_ones(provider, user):
    old = queued(user)
    generate_image_task(str(old.pk))
    old.refresh_from_db()
    storage, names = old.result_image.storage, [old.input_image.name, old.result_image.name]
    AIGeneration.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=31))

    stuck = queued(user)
    AIGeneration.objects.filter(pk=stuck.pk).update(status="running", started_at=timezone.now() - timedelta(hours=2))
    fresh = queued(user)

    assert cleanup_expired_generations() == {"recovered": 1, "purged": 1}

    assert not AIGeneration.objects.filter(pk=old.pk).exists()
    assert not any(storage.exists(name) for name in names)
    stuck.refresh_from_db()
    assert stuck.status == "failed"
    assert AIGeneration.objects.get(pk=fresh.pk).status == "queued"


def test_cleanup_is_scheduled():
    from config.celery import app

    tasks = {entry["task"] for entry in app.conf.beat_schedule.values()}
    assert "apps.ai_studio.tasks.cleanup_expired_generations" in tasks


def test_admin_lists_generations_and_budget(provider, user):
    from apps.accounts.models import User

    queued(user)
    admin = User.objects.create_superuser(email="root@example.com", password="Str0ng-Passw0rd!")
    client = Client()
    client.force_login(admin)
    assert client.get("/admin/ai_studio/aigeneration/").status_code == 200
    assert client.get("/admin/ai_studio/aidailybudget/").status_code == 200
    generation = AIGeneration.objects.first()
    page = client.get(f"/admin/ai_studio/aigeneration/{generation.pk}/change/")
    assert page.status_code == 200
    assert f"/admin/ai_studio/aigeneration/{generation.pk}/image/input/" in page.content.decode()
    image = client.get(f"/admin/ai_studio/aigeneration/{generation.pk}/image/input/")
    assert image.status_code == 200
    assert "no-store" in image["Cache-Control"]
    assert client.get(f"/admin/ai_studio/aigeneration/{generation.pk}/image/secret/").status_code == 404


def test_rejected_reservation_leaves_no_files(provider, user, settings, tmp_path):
    settings.AI_STUDIO_DAILY_QUOTA = 0
    from apps.ai_studio.services import AILimitReached

    with pytest.raises(AILimitReached):
        queued(user)
    assert AIGeneration.objects.count() == 0
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
