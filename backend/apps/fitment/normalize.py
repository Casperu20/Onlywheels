"""Canonical string formats so wheel/car specs can be compared with plain equality."""

import re
from decimal import Decimal, InvalidOperation

_TIRE_RE = re.compile(r"^\s*(\d{3})\s*/\s*(\d{2})\s*Z?R\s*(\d{2})\s*$", re.IGNORECASE)


def normalize_pcd(value: str) -> str:
    """'5×112.0' / '5X114,3' / '5 x 120' -> '5x112' / '5x114.3' / '5x120'."""
    cleaned = value.strip().lower().replace("×", "x").replace(",", ".").replace(" ", "")
    bolts, sep, diameter = cleaned.partition("x")
    try:
        if not sep or not bolts.isdigit():
            raise InvalidOperation
        number = Decimal(diameter)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid PCD: {value!r} (expected e.g. 5x112)") from exc
    return f"{int(bolts)}x{format(number.normalize(), 'f')}"


def normalize_tire_size(value: str) -> str:
    """'225/45r18' / '225 / 45 ZR 18' -> '225/45 R18'."""
    match = _TIRE_RE.match(value)
    if not match:
        raise ValueError(f"Invalid tire size: {value!r} (expected e.g. 225/45 R18)")
    width, aspect, rim = match.groups()
    return f"{width}/{aspect} R{rim}"


def format_tire_size(width_mm: int, aspect: int, rim_in: int) -> str:
    return f"{width_mm}/{aspect} R{rim_in}"


def normalize_thread(value: str) -> str:
    """'m14 × 1,5' -> 'M14x1.5'."""
    cleaned = value.strip().upper().replace("×", "X").replace(",", ".").replace(" ", "")
    return cleaned.replace("X", "x")
