import pytest

from apps.fitment.models import FitmentSpec
from apps.fitment.normalize import normalize_pcd, normalize_tire_size
from apps.vehicles import wheelsize
from apps.vehicles.models import VehicleGeneration, VehicleMake

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vehicles"


def _record(bolt="5x112", bore="57.1", thread="M14 x 1.5", wheels=None):
    return {
        "technical": {"bolt_pattern": bolt, "centre_bore": bore, "wheel_fasteners": {"thread_size": thread}},
        "wheels": wheels
        or [
            {"front": {"rim_diameter": 17, "rim_width": 7, "rim_offset": 49, "tire": "225/45R17"}, "rear": {}},
            {"front": {"rim_diameter": 18, "rim_width": 7.5, "rim_offset": 51, "tire": "225/40R18"}, "rear": {}},
        ],
    }


API = {
    "/makes/": [{"slug": "volkswagen", "name": "Volkswagen"}, {"slug": "dacia", "name": "Dacia"}],
    "/models/": [{"slug": "golf", "name": "Golf"}],
    "/generations/": [{"slug": "abc123", "name": "VIII", "platform": "CD1", "start": 2019, "end": 2099}],
    "/search/by_model/": [_record(), _record(wheels=[{"front": {"tire": "31x10.5R15"}, "rear": {}}])],
}


@pytest.fixture
def provider(settings, monkeypatch):
    from django.core.cache import cache

    cache.clear()
    settings.WHEEL_SIZE_API_KEY = "test-key"
    calls = []

    def fake_fetch(path, **params):
        calls.append(path)
        return API[path]

    monkeypatch.setattr(wheelsize, "fetch", fake_fetch)
    return calls


def test_disabled_without_key(api_client, settings, monkeypatch):
    settings.WHEEL_SIZE_API_KEY = ""
    monkeypatch.setattr(wheelsize, "fetch", lambda *a, **k: pytest.fail("must not call the API"))
    assert api_client.get(f"{BASE}/makes/").json() == []


def test_make_slug_changes_are_reconciled_by_unique_name(api_client, provider, monkeypatch):
    VehicleMake.objects.create(name="Mercedes-Benz", slug="mercedes-benz")
    monkeypatch.setattr(
        wheelsize,
        "fetch",
        lambda path, **params: [{"slug": "mercedes", "name": "Mercedes-Benz"}],
    )

    response = api_client.get(f"{BASE}/makes/")

    assert response.status_code == 200
    make = VehicleMake.objects.get(name="Mercedes-Benz")
    assert make.slug == "mercedes"


def test_lazy_import_cascade_is_fetched_once(api_client, provider):
    makes = api_client.get(f"{BASE}/makes/").json()
    assert [m["name"] for m in makes] == ["Dacia", "Volkswagen"]

    vw = VehicleMake.objects.get(slug="volkswagen")
    models = api_client.get(f"{BASE}/models/", {"make": str(vw.pk)}).json()
    generations = api_client.get(f"{BASE}/generations/", {"model": models[0]["id"]}).json()
    assert generations[0]["name"] == "VIII"
    assert generations[0]["year_from"] == 2019 and generations[0]["year_to"] is None

    detail = api_client.get(f"{BASE}/generations/{generations[0]['id']}/").json()
    fitment = detail["fitment"]
    assert fitment["pcd"] == normalize_pcd("5x112")
    assert fitment["et_min"] == 44 and fitment["et_max"] == 56
    assert (fitment["diameter_min"], fitment["diameter_max"]) == (17, 18)
    assert fitment["tire_sizes"] == [normalize_tire_size("225/40R18"), normalize_tire_size("225/45R17")]

    # Everything is stored now: repeating the same clicks costs no API requests.
    api_client.get(f"{BASE}/makes/")
    api_client.get(f"{BASE}/models/", {"make": str(vw.pk)})
    api_client.get(f"{BASE}/generations/", {"model": models[0]["id"]})
    api_client.get(f"{BASE}/generations/{generations[0]['id']}/")
    assert provider == ["/makes/", "/models/", "/generations/", "/search/by_model/"]


def test_provider_error_keeps_stored_data(api_client, settings, monkeypatch):
    settings.WHEEL_SIZE_API_KEY = "test-key"
    VehicleMake.objects.create(name="Dacia", slug="dacia")

    def broken(path, **params):
        raise wheelsize.WheelSizeError("quota exceeded")

    monkeypatch.setattr(wheelsize, "fetch", broken)
    response = api_client.get(f"{BASE}/makes/")
    assert response.status_code == 200
    assert [m["slug"] for m in response.json()] == ["dacia"]


def test_catalog_vehicle_filter_imports_missing_fitment(api_client, provider):
    api_client.get(f"{BASE}/makes/")
    vw = VehicleMake.objects.get(slug="volkswagen")
    model_id = api_client.get(f"{BASE}/models/", {"make": str(vw.pk)}).json()[0]["id"]
    api_client.get(f"{BASE}/generations/", {"model": model_id})
    generation = VehicleGeneration.objects.get(external_id="abc123")

    assert api_client.get("/api/v1/catalog/products/", {"vehicle": str(generation.pk)}).status_code == 200
    assert FitmentSpec.objects.filter(generation=generation).exists()


def test_records_without_usable_data_give_no_spec():
    assert wheelsize.fitment_from_records([_record(bolt="N/A")]) is None
    assert wheelsize.fitment_from_records([]) is None


def test_first_miss_works_when_celery_is_async_and_stale_refreshes_in_background(
    api_client, provider, settings, monkeypatch
):
    from datetime import timedelta

    from django.utils import timezone

    from apps.vehicles.tasks import sync_models_task

    settings.CELERY_TASK_ALWAYS_EAGER = False
    dispatched = []
    monkeypatch.setattr(sync_models_task, "delay", lambda make_id: dispatched.append(make_id))

    # First miss runs synchronously even with CELERY_TASK_ALWAYS_EAGER=False
    api_client.get(f"{BASE}/makes/")
    vw = VehicleMake.objects.get(slug="volkswagen")
    models = api_client.get(f"{BASE}/models/", {"make": str(vw.pk)}).json()
    assert len(models) == 1
    assert dispatched == []

    # Once synced, if it becomes stale (>30 days), it returns stored data and dispatches background refresh
    VehicleMake.objects.filter(pk=vw.pk).update(synced_at=timezone.now() - timedelta(days=31))
    models_stale = api_client.get(f"{BASE}/models/", {"make": str(vw.pk)}).json()
    assert len(models_stale) == 1
    assert dispatched == [str(vw.pk)]
