"""
Vehicle catalogue + fitment from the Wheel-Size API (https://developer.wheel-size.com/).

Active only when WHEEL_SIZE_API_KEY is set. Data is fetched the first time it is needed and stored in
our own tables (makes, models, generations, FitmentSpec), so the free Sandbox quota (300 requests/day)
is enough: one request per make list, per make, per model and per generation.
"""

import logging
from collections import Counter
from datetime import timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import VehicleGeneration, VehicleMake, VehicleModel

logger = logging.getLogger(__name__)

BASE_URL = "https://api.wheel-size.com/v2"
REFRESH_AFTER = timedelta(days=30)
ET_TOLERANCE = 5  # mm around the factory offsets that we still accept


class WheelSizeError(Exception):
    pass


def enabled() -> bool:
    return bool(settings.WHEEL_SIZE_API_KEY)


def fetch(path: str, **params) -> list[dict]:
    params = {**params, "region": settings.WHEEL_SIZE_REGION, "user_key": settings.WHEEL_SIZE_API_KEY}
    try:
        response = requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("data", [])
    except requests.HTTPError as exc:
        # Never put the URL in the message: it contains the API key.
        raise WheelSizeError(f"{path} returned HTTP {exc.response.status_code}") from None
    except (requests.RequestException, ValueError) as exc:
        raise WheelSizeError(f"{path} failed: {type(exc).__name__}") from None


def _fresh(synced_at) -> bool:
    return synced_at is not None and timezone.now() - synced_at < REFRESH_AFTER


def _safely(func, *args) -> None:
    """Provider problems (quota, network) must never break the shop: we just keep the stored data."""
    if not enabled():
        return
    try:
        func(*args)
    except WheelSizeError as exc:
        logger.warning("Wheel-Size sync skipped: %s", exc)


# --- makes / models / generations -----------------------------------------


def _sync_makes() -> None:
    if cache.get("wheelsize:makes"):
        return
    for item in fetch("/makes/"):
        VehicleMake.objects.update_or_create(slug=item["slug"], defaults={"name": item["name"]})
    cache.set("wheelsize:makes", True, REFRESH_AFTER.total_seconds())


def _sync_models(make: VehicleMake) -> None:
    if _fresh(make.synced_at):
        return
    for item in fetch("/models/", make=make.slug):
        VehicleModel.objects.update_or_create(make=make, slug=item["slug"], defaults={"name": item["name"]})
    make.synced_at = timezone.now()
    make.save(update_fields=["synced_at", "updated_at"])


@transaction.atomic
def _sync_generations(model: VehicleModel) -> None:
    if _fresh(model.synced_at):
        return
    current_year = timezone.now().year
    for item in fetch("/generations/", make=model.make.slug, model=model.slug):
        name = item.get("name") or item.get("platform") or str(item["start"])
        taken = VehicleGeneration.objects.filter(model=model, name=name).exclude(external_id=item["slug"])
        if taken.exists():
            name = f"{name} {item['start']}–{item['end']}"
        VehicleGeneration.objects.update_or_create(
            model=model,
            external_id=item["slug"],
            defaults={
                "name": name[:100],
                "year_from": item["start"],
                "year_to": None if item["end"] >= current_year else item["end"],
            },
        )
    model.synced_at = timezone.now()
    model.save(update_fields=["synced_at", "updated_at"])


def ensure_makes() -> None:
    _safely(_sync_makes)


def ensure_models(make_id) -> None:
    make = VehicleMake.objects.filter(pk=make_id).first()
    if make:
        _safely(_sync_models, make)


def ensure_generations(model_id) -> None:
    model = VehicleModel.objects.select_related("make").filter(pk=model_id).first()
    if model:
        _safely(_sync_generations, model)


# --- fitment ----------------------------------------------------------------


def fitment_from_records(records: list[dict]) -> dict | None:
    """Turn the factory/aftermarket wheel list of all engine variants into one FitmentSpec."""
    from apps.fitment.normalize import normalize_pcd, normalize_thread, normalize_tire_size

    patterns, bores, threads = Counter(), Counter(), Counter()
    diameters, widths, offsets, tires = set(), set(), set(), set()
    for record in records:
        technical = record.get("technical") or {}
        if technical.get("bolt_pattern") not in (None, "", "N/A"):
            patterns[technical["bolt_pattern"]] += 1
        try:
            bores[Decimal(str(technical.get("centre_bore")))] += 1
        except InvalidOperation:
            pass
        thread = (technical.get("wheel_fasteners") or {}).get("thread_size")
        if thread:
            threads[thread] += 1
        for pair in record.get("wheels") or []:
            for side in (pair.get("front") or {}, pair.get("rear") or {}):
                if side.get("rim_diameter"):
                    diameters.add(int(side["rim_diameter"]))
                if side.get("rim_width"):
                    widths.add(Decimal(str(side["rim_width"])))
                if side.get("rim_offset") is not None:
                    offsets.add(int(side["rim_offset"]))
                if side.get("tire"):
                    try:
                        tires.add(normalize_tire_size(side["tire"]))
                    except ValueError:
                        pass  # imperial / LT sizes are not sold in this shop

    if not patterns or not bores or not diameters or not widths or not offsets:
        return None
    try:
        pcd = normalize_pcd(patterns.most_common(1)[0][0])
    except ValueError:
        return None
    try:
        thread = normalize_thread(threads.most_common(1)[0][0]) if threads else ""
    except ValueError:
        thread = ""
    return {
        "pcd": pcd,
        "center_bore_mm": bores.most_common(1)[0][0],
        "et_min": min(offsets) - ET_TOLERANCE,
        "et_max": max(offsets) + ET_TOLERANCE,
        "diameter_min": min(diameters),
        "diameter_max": max(diameters),
        "width_min": min(widths),
        "width_max": max(widths),
        "thread_size": thread,
        "tire_sizes": sorted(tires),
        "notes": "Imported from Wheel-Size API",
    }


def _sync_fitment(generation: VehicleGeneration) -> None:
    from apps.fitment.models import FitmentSpec

    if not generation.external_id or _fresh(generation.fitment_checked_at):
        return
    model = generation.model
    records = fetch("/search/by_model/", make=model.make.slug, model=model.slug, generation=generation.external_id)
    data = fitment_from_records(records)
    if data:
        FitmentSpec.objects.update_or_create(generation=generation, defaults=data)
    generation.fitment_checked_at = timezone.now()
    generation.save(update_fields=["fitment_checked_at", "updated_at"])


def ensure_fitment(generation_id) -> None:
    generation = VehicleGeneration.objects.select_related("model__make").filter(pk=generation_id).first()
    if generation:
        _safely(_sync_fitment, generation)
