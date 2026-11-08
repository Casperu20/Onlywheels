import io
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.ai_studio.models import AIDailyBudget, AIGeneration
from apps.ai_studio.providers import AIConfigurationError
from apps.ai_studio.services import today_budget
from apps.catalog.models import ProductType
from tests.factories import make_product, make_tire, make_variant

pytestmark = pytest.mark.django_db

URL = "/api/v1/ai/generations/"
ESTIMATE = Decimal("0.0400")


def image_bytes(fmt="JPEG", size=(640, 480), exif=False, mode="RGB"):
    buffer = io.BytesIO()
    image = Image.new(mode, size, "red" if mode == "RGB" else 0)
    kwargs = {}
    if exif:
        data = Image.Exif()
        data[0x010F] = "SecretCam"  # Make
        kwargs["exif"] = data.tobytes()
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def upload(data=None, name="car.jpg", content_type="image/jpeg"):
    return SimpleUploadedFile(name, data if data is not None else image_bytes(), content_type=content_type)


@pytest.fixture
def provider(settings, tmp_path):
    settings.AI_STUDIO_PROVIDER = "replicate"
    settings.AI_STUDIO_PRIVATE_ROOT = str(tmp_path)
    settings.AI_STUDIO_DAILY_QUOTA = 5
    settings.AI_STUDIO_DAILY_BUDGET_USD = Decimal("5.00")
    fake = Mock()
    fake.name = "replicate"
    fake.estimate_cost.return_value = ESTIMATE
    fake.check_configuration.return_value = None
    with patch("apps.ai_studio.services.get_image_provider", return_value=fake):
        yield fake


@pytest.fixture
def client(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


@pytest.fixture
def other_client(db):
    other = User.objects.create_user(email="other@example.com", password="Str0ng-Passw0rd!")
    api = APIClient()
    api.force_authenticate(other)
    return api


def create(client, **fields):
    payload = {"image": upload(), "scene": "city_night", "style": "photo", **fields}
    return client.post(URL, payload, format="multipart")


def error_fields(response) -> dict:
    return response.json()["error"].get("fields", {})


# --- Configuration ------------------------------------------------------------------------


def test_anonymous_users_cannot_use_the_studio():
    api = APIClient()
    assert api.get(URL).status_code == 401
    assert api.post(URL, {}, format="multipart").status_code == 401
    assert api.get("/api/v1/ai/studio/").status_code == 401


def test_studio_info_reports_options_and_quota(client, provider):
    body = client.get("/api/v1/ai/studio/").json()
    assert body["enabled"] is True
    assert body["daily_limit"] == 5
    assert body["remaining_today"] == 5
    assert {"value": "city_night", "label": "City at night"} in body["scenes"]
    assert any(style["value"] == "photo" for style in body["styles"])
    assert body["max_upload_bytes"] == 10 * 1024 * 1024


def test_disabled_studio_rejects_jobs_visibly(client, settings):
    settings.AI_STUDIO_PROVIDER = ""
    assert client.get("/api/v1/ai/studio/").json()["enabled"] is False
    response = create(client)
    assert response.status_code == 503
    assert AIGeneration.objects.count() == 0


def test_misconfigured_provider_rejects_jobs_without_leaking_details(client, provider):
    provider.check_configuration.side_effect = AIConfigurationError("REPLICATE_API_TOKEN is required.")
    assert client.get("/api/v1/ai/studio/").json()["enabled"] is False
    response = create(client)
    assert response.status_code == 503
    assert "REPLICATE_API_TOKEN" not in response.content.decode()
    assert AIGeneration.objects.count() == 0


# --- Creating jobs ------------------------------------------------------------------------


def test_valid_upload_queues_a_private_generation(client, provider, user, tmp_path):
    variant = make_variant(make_product(type=ProductType.WHEEL))
    response = create(client, variant=str(variant.pk), image=upload(image_bytes(exif=True)))

    assert response.status_code == 202, response.content
    body = response.json()
    generation = AIGeneration.objects.get(pk=body["id"])
    assert (generation.user, generation.status, generation.variant) == (user, "queued", variant)
    assert generation.source == "user_photo"
    assert generation.estimated_cost == ESTIMATE
    assert body["status"] == "queued"
    assert body["input_url"] == f"/api/v1/ai/generations/{generation.pk}/input/"
    assert body["result_url"] is None
    assert str(tmp_path) in generation.input_image.path
    assert "media" not in generation.input_image.name
    with generation.input_image.open("rb") as stored:
        stored_image = Image.open(stored)
        assert stored_image.format == "JPEG"
        assert 0x010F not in stored_image.getexif()  # metadata (e.g. GPS) stripped
    assert today_budget().reserved_usd == ESTIMATE


@pytest.mark.parametrize(
    ("data", "name", "content_type"),
    [
        (b"not an image at all", "car.jpg", "image/jpeg"),
        (image_bytes("GIF", mode="P"), "car.gif", "image/gif"),
        (image_bytes(size=(100, 100)), "tiny.jpg", "image/jpeg"),
    ],
)
def test_invalid_images_are_rejected_before_storage(client, provider, data, name, content_type):
    response = create(client, image=upload(data, name, content_type))
    assert response.status_code == 400
    assert "image" in error_fields(response)
    assert AIGeneration.objects.count() == 0
    provider.estimate_cost.assert_not_called()


def test_png_and_webp_uploads_are_accepted(client, provider):
    assert create(client, image=upload(image_bytes("PNG"), "car.png", "image/png")).status_code == 202
    assert create(client, image=upload(image_bytes("WEBP"), "car.webp", "image/webp")).status_code == 202


def test_oversized_upload_is_rejected(client, provider, settings):
    settings.AI_STUDIO_MAX_UPLOAD_BYTES = 1024
    response = create(client)
    assert response.status_code == 400
    assert "image" in error_fields(response)
    assert AIGeneration.objects.count() == 0


def test_too_many_megapixels_are_rejected(client, provider, settings):
    settings.AI_STUDIO_MAX_PIXELS = 640 * 480 - 1
    response = create(client)
    assert response.status_code == 400
    assert AIGeneration.objects.count() == 0


def test_unknown_scene_and_non_wheel_variant_are_rejected(client, provider):
    assert "scene" in error_fields(create(client, scene="moon"))
    tire = make_tire(make_product(type=ProductType.TIRE))
    assert "variant" in error_fields(create(client, variant=str(tire.pk)))
    assert AIGeneration.objects.count() == 0


def test_user_daily_quota(client, provider):
    for _ in range(5):
        assert create(client).status_code == 202
    response = create(client)
    assert response.status_code == 429
    assert AIGeneration.objects.count() == 5
    assert client.get("/api/v1/ai/studio/").json()["remaining_today"] == 0


def test_failed_jobs_do_not_count_towards_the_quota(client, provider):
    for _ in range(5):
        create(client)
    AIGeneration.objects.filter(pk=AIGeneration.objects.first().pk).update(status="failed")
    assert create(client).status_code == 202


def test_global_daily_budget(client, other_client, provider, settings):
    settings.AI_STUDIO_DAILY_BUDGET_USD = Decimal("0.10")
    assert create(client).status_code == 202
    assert create(other_client).status_code == 202
    response = create(client)
    assert response.status_code == 429
    assert "today" in response.json()["error"]["message"].lower()
    assert today_budget().reserved_usd == Decimal("0.08")


def test_spent_budget_counts_towards_the_ceiling(client, provider, settings):
    settings.AI_STUDIO_DAILY_BUDGET_USD = Decimal("1.00")
    AIDailyBudget.objects.filter(pk=today_budget().pk).update(spent_usd=Decimal("0.97"))
    assert create(client).status_code == 429


# --- Reading, streaming, deleting ---------------------------------------------------------


def listed_ids(response) -> list[str]:
    body = response.json()
    return [item["id"] for item in (body["results"] if isinstance(body, dict) else body)]


def test_owner_lists_and_reads_only_their_generations(client, other_client, provider):
    mine = create(client).json()["id"]
    theirs = create(other_client).json()["id"]

    assert listed_ids(client.get(URL)) == [mine]
    assert client.get(f"{URL}{mine}/").status_code == 200
    for path in ("", "input/", "result/"):
        assert client.get(f"{URL}{theirs}/{path}").status_code == 404
    assert client.delete(f"{URL}{theirs}/").status_code == 404
    assert client.post(f"{URL}{theirs}/retry/").status_code == 404


def test_owner_streams_the_private_input(client, provider):
    generation_id = create(client).json()["id"]
    response = client.get(f"{URL}{generation_id}/input/")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"
    assert "no-store" in response["Cache-Control"]
    assert b"".join(response.streaming_content).startswith(b"\xff\xd8")
    assert client.get(f"{URL}{generation_id}/result/").status_code == 404


def test_staff_can_stream_but_not_list_other_users_images(client, provider, db):
    generation_id = create(client).json()["id"]
    staff = User.objects.create_user(email="staff@example.com", password="Str0ng-Passw0rd!", is_staff=True)
    api = APIClient()
    api.force_authenticate(staff)
    assert api.get(f"{URL}{generation_id}/input/").status_code == 200
    assert listed_ids(api.get(URL)) == []


def test_delete_removes_files_releases_queued_budget_but_keeps_quota(client, provider):
    generation_id = create(client).json()["id"]
    generation = AIGeneration.objects.get(pk=generation_id)
    storage, name = generation.input_image.storage, generation.input_image.name
    assert storage.exists(name)

    assert client.delete(f"{URL}{generation_id}/").status_code == 204

    assert not storage.exists(name)
    assert client.get(f"{URL}{generation_id}/").status_code == 404
    assert listed_ids(client.get(URL)) == []
    generation.refresh_from_db()
    assert generation.deleted_at is not None
    assert generation.status == "cancelled"
    assert not generation.input_image
    assert today_budget().reserved_usd == Decimal("0")
    assert client.get("/api/v1/ai/studio/").json()["remaining_today"] == 4


def test_retry_a_failed_generation_reuses_its_photo(client, provider):
    generation_id = create(client).json()["id"]
    AIGeneration.objects.filter(pk=generation_id).update(status="failed", error="Provider timed out.")

    response = client.post(f"{URL}{generation_id}/retry/")

    assert response.status_code == 202, response.content
    retried = AIGeneration.objects.get(pk=response.json()["id"])
    assert str(retried.pk) != generation_id
    assert (retried.scene, retried.style, retried.status) == ("city_night", "photo", "queued")
    original = AIGeneration.objects.get(pk=generation_id)
    assert retried.input_image.name != original.input_image.name
    with retried.input_image.open("rb") as copy:
        assert copy.read().startswith(b"\xff\xd8")


def test_only_failed_generations_can_be_retried(client, provider):
    generation_id = create(client).json()["id"]
    assert client.post(f"{URL}{generation_id}/retry/").status_code == 400


# --- GDPR --------------------------------------------------------------------------------


def test_account_deletion_removes_ai_images(client, provider, user):
    from apps.accounts.services import delete_account

    generation = AIGeneration.objects.get(pk=create(client).json()["id"])
    storage, name = generation.input_image.storage, generation.input_image.name

    delete_account(user)

    assert not storage.exists(name)
    assert not AIGeneration.objects.filter(user=user).exists()


def test_export_lists_ai_generations_without_image_urls(client, provider, user):
    from apps.accounts.services import export_user_data

    create(client)
    exported = export_user_data(user)["ai_generations"]
    assert exported[0]["scene"] == "city_night"
    assert "input_image" not in exported[0]
