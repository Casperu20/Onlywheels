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

from dataclasses import dataclass, field

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


def _in_range(value, low, high) -> bool:
    return value is not None and low <= value <= high


def check_variant(spec: FitmentSpec, variant: ProductVariant) -> FitmentResult:
    product_type = variant.product.type
    issues: list[str] = []
    needs_rings = False

    if product_type == ProductType.ACCESSORY:
        if variant.thread_size and spec.thread_size and variant.thread_size != spec.thread_size:
            issues.append(THREAD_MISMATCH)
        return FitmentResult(fits=not issues, issues=tuple(issues))

    if product_type in (ProductType.WHEEL, ProductType.SET):
        if variant.pcd != spec.pcd:
            issues.append(PCD_MISMATCH)
        if variant.center_bore_mm is None or variant.center_bore_mm < spec.center_bore_mm:
            issues.append(CENTER_BORE_TOO_SMALL)
        elif variant.center_bore_mm > spec.center_bore_mm:
            needs_rings = True
        if not _in_range(variant.et_mm, spec.et_min, spec.et_max):
            issues.append(OFFSET_OUT_OF_RANGE)
        if not _in_range(variant.diameter_in, spec.diameter_min, spec.diameter_max):
            issues.append(DIAMETER_OUT_OF_RANGE)
        if not _in_range(variant.width_in, spec.width_min, spec.width_max):
            issues.append(WIDTH_OUT_OF_RANGE)

    checks_tire = product_type == ProductType.TIRE or (
        product_type == ProductType.SET and variant.tire_size
    )
    if checks_tire and variant.tire_size not in spec.tire_sizes:
        issues.append(TIRE_SIZE_NOT_OEM)

    return FitmentResult(
        fits=not issues, needs_hub_rings=needs_rings and not issues, issues=tuple(issues)
    )


def compatible_variants_q(spec: FitmentSpec) -> Q:
    """Q object for ProductVariant querysets, equivalent to check_variant(...).fits."""
    wheel = Q(
        pcd=spec.pcd,
        center_bore_mm__gte=spec.center_bore_mm,
        et_mm__gte=spec.et_min,
        et_mm__lte=spec.et_max,
        diameter_in__gte=spec.diameter_min,
        diameter_in__lte=spec.diameter_max,
        width_in__gte=spec.width_min,
        width_in__lte=spec.width_max,
    )
    tire = Q(tire_size__in=spec.tire_sizes)
    thread_ok = Q(thread_size="") | Q(thread_size=spec.thread_size) if spec.thread_size else Q()

    return (
        (Q(product__type=ProductType.WHEEL) & wheel)
        | (Q(product__type=ProductType.TIRE) & tire)
        | (Q(product__type=ProductType.SET) & wheel & (Q(tire_size="") | tire))
        | (Q(product__type=ProductType.ACCESSORY) & thread_ok)
    )


def get_spec(generation_id) -> FitmentSpec | None:
    return FitmentSpec.objects.filter(generation_id=generation_id).first()
