import io
import json
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests
from PIL import Image

from apps.ai_studio.providers import (
    AIConfigurationError,
    AIModerationError,
    AIProviderError,
    GenerationRequest,
    get_image_provider,
)
from apps.ai_studio.providers.fal import FalProvider
from apps.ai_studio.providers.replicate import ReplicateProvider


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


def response(status=200, payload=None, content=b"", headers=None):
    mock = Mock(spec=requests.Response)
    mock.status_code = status
    mock.ok = status < 400
    mock.headers = headers or {"Content-Type": "application/json"}
    mock.content = content or (json.dumps(payload).encode() if payload is not None else b"")
    mock.text = mock.content.decode(errors="replace")
    mock.json.side_effect = (lambda: payload) if payload is not None else ValueError("no json")
    mock.iter_content = lambda chunk_size=65536: iter([mock.content])
    return mock


REQUEST = GenerationRequest(
    prompt="Replace the wheels", scene="city_night", angle="", style="photo", image_bytes=b"\xff\xd8jpeg"
)


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("apps.ai_studio.providers.base.time.sleep"):
        yield


@pytest.fixture
def replicate(settings):
    settings.REPLICATE_API_TOKEN = "r8_test"
    settings.REPLICATE_MODEL = "black-forest-labs/flux-kontext-pro"
    settings.REPLICATE_COST_PER_IMAGE_USD = Decimal("0.04")
    settings.AI_STUDIO_PROVIDER_TIMEOUT_SECONDS = 180
    return ReplicateProvider()


@pytest.fixture
def fal(settings):
    settings.FAL_KEY = "fal-test-key"
    settings.FAL_MODEL = "fal-ai/flux-pro/kontext"
    settings.FAL_COST_PER_IMAGE_USD = Decimal("0.04")
    settings.AI_STUDIO_PROVIDER_TIMEOUT_SECONDS = 180
    return FalProvider()


# --- Registry ------------------------------------------------------------------------------


def test_registry(settings):
    settings.AI_STUDIO_PROVIDER = ""
    assert get_image_provider() is None
    assert isinstance(get_image_provider("replicate"), ReplicateProvider)
    assert isinstance(get_image_provider("FAL"), FalProvider)
    with pytest.raises(AIConfigurationError):
        get_image_provider("midjourney")


def test_missing_credentials_are_configuration_errors(settings):
    settings.REPLICATE_API_TOKEN = ""
    settings.FAL_KEY = ""
    for provider in (ReplicateProvider(), FalProvider()):
        with pytest.raises(AIConfigurationError):
            provider.check_configuration()


def test_cost_estimates_come_from_settings(replicate, fal, settings):
    settings.FAL_COST_PER_IMAGE_USD = Decimal("0.039")
    assert replicate.estimate_cost() == Decimal("0.04")
    assert fal.estimate_cost() == Decimal("0.039")


# --- Replicate -----------------------------------------------------------------------------

FILE = {"id": "file-1", "urls": {"get": "https://api.replicate.com/v1/files/file-1/download"}}


def prediction(status, output=None, error=None):
    return {
        "id": "pred-1",
        "status": status,
        "output": output,
        "error": error,
        "urls": {
            "get": "https://api.replicate.com/v1/predictions/pred-1",
            "cancel": "https://api.replicate.com/v1/predictions/pred-1/cancel",
        },
    }


def test_replicate_uploads_privately_runs_polls_and_downloads(replicate):
    output_url = "https://replicate.delivery/out.png"
    posts = [response(201, FILE), response(201, prediction("starting"))]
    gets = [response(200, prediction("succeeded", output=output_url)), response(200, content=png_bytes())]
    with (
        patch("requests.post", side_effect=posts) as post,
        patch("requests.get", side_effect=gets) as get,
        patch("requests.delete", return_value=response(204)) as delete,
    ):
        result = replicate.generate(REQUEST)

    assert result.image_bytes == png_bytes()
    assert result.content_type == "image/png"
    assert result.cost is None
    assert result.provider_job_id == "pred-1"

    upload_call, predict_call = post.call_args_list
    assert upload_call.args[0] == "https://api.replicate.com/v1/files"
    assert upload_call.kwargs["headers"]["Authorization"] == "Bearer r8_test"
    assert upload_call.kwargs["files"]["content"][1] == REQUEST.image_bytes
    assert predict_call.args[0] == "https://api.replicate.com/v1/predictions"
    body = predict_call.kwargs["json"]
    assert body["version"] == "black-forest-labs/flux-kontext-pro"
    assert body["input"]["prompt"] == "Replace the wheels"
    assert body["input"]["input_image"] == FILE["urls"]["get"]
    assert predict_call.kwargs["headers"]["Prefer"].startswith("wait=")
    assert get.call_args_list[0].args[0] == "https://api.replicate.com/v1/predictions/pred-1"
    assert get.call_args_list[1].args[0] == output_url
    delete.assert_called_once()
    assert delete.call_args.args[0] == "https://api.replicate.com/v1/files/file-1"


def test_replicate_nano_banana_takes_a_list_of_images(replicate, settings):
    settings.REPLICATE_MODEL = "google/nano-banana"
    posts = [response(201, FILE), response(201, prediction("succeeded", output="https://x/out.png"))]
    with (
        patch("requests.post", side_effect=posts) as post,
        patch("requests.get", return_value=response(200, content=png_bytes())),
        patch("requests.delete", return_value=response(204)),
    ):
        replicate.generate(REQUEST)
    assert post.call_args_list[1].kwargs["json"]["input"]["image_input"] == [FILE["urls"]["get"]]


def test_replicate_safety_failure_is_moderation(replicate):
    posts = [response(201, FILE), response(201, prediction("failed", error="Flagged as sensitive (NSFW)."))]
    with (
        patch("requests.post", side_effect=posts),
        patch("requests.delete", return_value=response(204)) as delete,
        pytest.raises(AIModerationError),
    ):
        replicate.generate(REQUEST)
    delete.assert_called_once()


def test_replicate_rejected_request_is_not_charged(replicate):
    posts = [response(201, FILE), response(422, {"detail": "invalid input"})]
    with (
        patch("requests.post", side_effect=posts),
        patch("requests.delete", return_value=response(204)),
        pytest.raises(AIProviderError) as raised,
    ):
        replicate.generate(REQUEST)
    assert raised.value.charged is False


def test_replicate_bad_token_is_a_configuration_error(replicate):
    with (
        patch("requests.post", return_value=response(401, {"detail": "Unauthenticated"})),
        pytest.raises(AIConfigurationError),
    ):
        replicate.generate(REQUEST)


def test_replicate_timeout_after_submitting_has_unknown_charge(replicate):
    posts = [response(201, FILE), requests.Timeout("read timed out")]
    with (
        patch("requests.post", side_effect=posts),
        patch("requests.delete", return_value=response(204)),
        pytest.raises(AIProviderError) as raised,
    ):
        replicate.generate(REQUEST)
    assert raised.value.charged is None


def test_replicate_deadline_cancels_the_prediction(replicate, settings):
    settings.AI_STUDIO_PROVIDER_TIMEOUT_SECONDS = 0
    posts = [response(201, FILE), response(201, prediction("processing")), response(200, prediction("canceled"))]
    with (
        patch("requests.post", side_effect=posts) as post,
        patch("requests.get", return_value=response(200, prediction("processing"))),
        patch("requests.delete", return_value=response(204)),
        pytest.raises(AIProviderError) as raised,
    ):
        replicate.generate(REQUEST)
    assert raised.value.charged is None
    assert post.call_args_list[-1].args[0].endswith("/predictions/pred-1/cancel")


def test_replicate_rejects_non_image_output(replicate):
    posts = [response(201, FILE), response(201, prediction("succeeded", output=["https://x/out.png"]))]
    with (
        patch("requests.post", side_effect=posts),
        patch("requests.get", return_value=response(200, content=b"<html>nope</html>")),
        patch("requests.delete", return_value=response(204)),
        pytest.raises(AIProviderError),
    ):
        replicate.generate(REQUEST)


# --- fal.ai --------------------------------------------------------------------------------

QUEUE = "https://queue.fal.run/fal-ai/flux-pro/kontext/requests/req-1"
SUBMITTED = {
    "request_id": "req-1",
    "status_url": f"{QUEUE}/status",
    "response_url": QUEUE,
    "cancel_url": f"{QUEUE}/cancel",
}


def test_fal_submits_data_uri_without_storing_io_and_fetches_result(fal):
    result_payload = {"images": [{"url": "https://v3b.fal.media/files/out.png", "content_type": "image/png"}]}
    gets = [
        response(200, {"status": "IN_PROGRESS"}),
        response(200, {"status": "COMPLETED"}),
        response(200, result_payload),
        response(200, content=png_bytes()),
    ]
    with (
        patch("requests.post", return_value=response(200, SUBMITTED)) as post,
        patch("requests.get", side_effect=gets) as get,
    ):
        result = fal.generate(REQUEST)

    assert result.image_bytes == png_bytes()
    assert result.provider_job_id == "req-1"
    assert post.call_args.args[0] == "https://queue.fal.run/fal-ai/flux-pro/kontext"
    headers = post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Key fal-test-key"
    assert headers["X-Fal-Store-IO"] == "0"
    assert json.loads(headers["X-Fal-Object-Lifecycle-Preference"])["expiration_duration_seconds"] <= 3600
    body = post.call_args.kwargs["json"]
    assert body["prompt"] == "Replace the wheels"
    assert body["image_url"].startswith("data:image/jpeg;base64,")
    assert get.call_args_list[0].args[0] == SUBMITTED["status_url"]
    assert get.call_args_list[2].args[0] == SUBMITTED["response_url"]


def test_fal_content_policy_violation_is_moderation(fal):
    violation = {"detail": [{"type": "content_policy_violation", "msg": "flagged", "loc": ["body", "image_url"]}]}
    gets = [response(200, {"status": "COMPLETED"}), response(422, violation)]
    with (
        patch("requests.post", return_value=response(200, SUBMITTED)),
        patch("requests.get", side_effect=gets),
        pytest.raises(AIModerationError),
    ):
        fal.generate(REQUEST)


def test_fal_nsfw_flag_in_result_is_moderation(fal):
    payload = {"images": [{"url": "https://x/out.png"}], "has_nsfw_concepts": [True]}
    gets = [response(200, {"status": "COMPLETED"}), response(200, payload)]
    with (
        patch("requests.post", return_value=response(200, SUBMITTED)),
        patch("requests.get", side_effect=gets),
        pytest.raises(AIModerationError),
    ):
        fal.generate(REQUEST)


def test_fal_server_errors_are_not_charged(fal):
    gets = [response(200, {"status": "COMPLETED"}), response(500, {"detail": "boom"})]
    with (
        patch("requests.post", return_value=response(200, SUBMITTED)),
        patch("requests.get", side_effect=gets),
        pytest.raises(AIProviderError) as raised,
    ):
        fal.generate(REQUEST)
    assert raised.value.charged is False


def test_fal_bad_key_is_a_configuration_error(fal):
    with (
        patch("requests.post", return_value=response(401, {"detail": "Unauthorized"})),
        pytest.raises(AIConfigurationError),
    ):
        fal.generate(REQUEST)


def test_fal_deadline_cancels_the_request(fal, settings):
    settings.AI_STUDIO_PROVIDER_TIMEOUT_SECONDS = 0
    with (
        patch("requests.post", return_value=response(200, SUBMITTED)),
        patch("requests.get", return_value=response(200, {"status": "IN_QUEUE"})),
        patch("requests.put", return_value=response(202, {})) as put,
        pytest.raises(AIProviderError) as raised,
    ):
        fal.generate(REQUEST)
    assert raised.value.charged is None
    assert put.call_args.args[0] == SUBMITTED["cancel_url"]
