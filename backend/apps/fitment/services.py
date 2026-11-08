"""
"Which wheels fit my car" engine.

Rules (wheels and the wheel part of complete sets):
- PCD must match exactly.
- Wheel center bore must be >= the car's hub. Larger bores fit with hub-centric rings.
- ET (offset), diameter and width must be inside the generation's allowed range.
Tires (and the tire part of sets) must be one of the generation's OEM tire sizes.
Accessories fit unless they have a thread size that differs from the car's.

`check_variant` (one variant, with reasons) and `compatible_variants_q` (database filter)
implement the same rules; tests keep them in sync.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import reduce
from operator import and_

from django.db.models import Q

from apps.catalog.models import ProductType, ProductVariant

from .models import FitmentSpec

PCD_MISMATCH = "pcd_mismatch"
CENTER_BORE_TOO_SMALL = "center_bore_too_small"
OFFSET_OUT_OF_RANGE = "offset_out_of_range"
DIAMETER_OUT_OF_RANGE = "diameter_out_of_range"
WIDTH_OUT_OF_RANGE = "width_out_of_range"
TIRE_SIZE_NOT_OEM = "tire_size_not_oem"
THREAD_MISMATCH = "thread_mismatch"


@dataclass(frozen=True)
class FitmentResult:
    fits: bool
    needs_hub_rings: bool = False
    issues: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FitmentRule:
    """Single source of truth for both in-memory validation and ORM queryset filtering."""

    code: str
    matches: Callable[[FitmentSpec, ProductVariant], bool]
    to_q: Callable[[FitmentSpec], Q]


def _in_range(value, low, high) -> bool:
    return value is not None and low <= value <= high


WHEEL_RULES: tuple[FitmentRule, ...] = (
    FitmentRule(
        code=PCD_MISMATCH,
        matches=lambda s, v: v.pcd == s.pcd,
        to_q=lambda s: Q(pcd=s.pcd),
    ),
    FitmentRule(
        code=CENTER_BORE_TOO_SMALL,
        matches=lambda s, v: v.center_bore_mm is not None and v.center_bore_mm >= s.center_bore_mm,
        to_q=lambda s: Q(center_bore_mm__gte=s.center_bore_mm),
    ),
    FitmentRule(
        code=OFFSET_OUT_OF_RANGE,
        matches=lambda s, v: _in_range(v.et_mm, s.et_min, s.et_max),
        to_q=lambda s: Q(et_mm__gte=s.et_min, et_mm__lte=s.et_max),
    ),
    FitmentRule(
        code=DIAMETER_OUT_OF_RANGE,
        matches=lambda s, v: _in_range(v.diameter_in, s.diameter_min, s.diameter_max),
        to_q=lambda s: Q(diameter_in__gte=s.diameter_min, diameter_in__lte=s.diameter_max),
    ),
    FitmentRule(
        code=WIDTH_OUT_OF_RANGE,
        matches=lambda s, v: _in_range(v.width_in, s.width_min, s.width_max),
        to_q=lambda s: Q(width_in__gte=s.width_min, width_in__lte=s.width_max),
    ),
)

TIRE_RULE = FitmentRule(
    code=TIRE_SIZE_NOT_OEM,
    matches=lambda s, v: v.tire_size in s.tire_sizes,
    to_q=lambda s: Q(tire_size__in=s.tire_sizes),
)

ACCESSORY_RULE = FitmentRule(
    code=THREAD_MISMATCH,
    matches=lambda s, v: not (v.thread_size and s.thread_size) or v.thread_size == s.thread_size,
    to_q=lambda s: Q(thread_size="") | Q(thread_size=s.thread_size) if s.thread_size else Q(),
)


def check_variant(spec: FitmentSpec, variant: ProductVariant) -> FitmentResult:
    product_type = variant.product.type
    if product_type == ProductType.ACCESSORY:
        issues = () if ACCESSORY_RULE.matches(spec, variant) else (ACCESSORY_RULE.code,)
        return FitmentResult(fits=not issues, issues=issues)

    issues_list: list[str] = []
    needs_rings = False

    if product_type in (ProductType.WHEEL, ProductType.SET):
        for rule in WHEEL_RULES:
            if not rule.matches(spec, variant):
                issues_list.append(rule.code)
        if variant.center_bore_mm is not None and variant.center_bore_mm > spec.center_bore_mm:
            needs_rings = True

    checks_tire = product_type == ProductType.TIRE or (
        product_type == ProductType.SET and bool(variant.tire_size)
    )
    if checks_tire and not TIRE_RULE.matches(spec, variant):
        issues_list.append(TIRE_RULE.code)

    return FitmentResult(
        fits=not issues_list,
        needs_hub_rings=needs_rings and not issues_list,
        issues=tuple(issues_list),
    )


def compatible_variants_q(spec: FitmentSpec) -> Q:
    """Q object for ProductVariant querysets, derived from the same rules as check_variant(...)."""
    wheel_q = reduce(and_, (rule.to_q(spec) for rule in WHEEL_RULES))
    tire_q = TIRE_RULE.to_q(spec)
    thread_q = ACCESSORY_RULE.to_q(spec)

    return (
        (Q(product__type=ProductType.WHEEL) & wheel_q)
        | (Q(product__type=ProductType.TIRE) & tire_q)
        | (Q(product__type=ProductType.SET) & wheel_q & (Q(tire_size="") | tire_q))
        | (Q(product__type=ProductType.ACCESSORY) & thread_q)
    )


def get_spec(generation_id) -> FitmentSpec | None:
    from apps.vehicles import wheelsize

    spec = FitmentSpec.objects.filter(generation_id=generation_id).first()
    if spec is None:
        wheelsize.ensure_fitment(generation_id)
        spec = FitmentSpec.objects.filter(generation_id=generation_id).first()
    elif wheelsize.enabled():
        wheelsize.ensure_fitment(generation_id)
    return spec
