import pytest

from apps.fitment.normalize import normalize_pcd, normalize_thread, normalize_tire_size


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5x112", "5x112"),
        ("5×112.0", "5x112"),
        ("5X114,3", "5x114.3"),
        (" 5 x 120 ", "5x120"),
        ("4x100.00", "4x100"),
    ],
)
def test_normalize_pcd(raw, expected):
    assert normalize_pcd(raw) == expected


@pytest.mark.parametrize("raw", ["", "5x", "x112", "five x 112", "5-112"])
def test_normalize_pcd_rejects_garbage(raw):
    with pytest.raises(ValueError):
        normalize_pcd(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("225/45 R18", "225/45 R18"), ("225/45r18", "225/45 R18"), ("225 / 40 ZR 19", "225/40 R19")],
)
def test_normalize_tire_size(raw, expected):
    assert normalize_tire_size(raw) == expected


def test_normalize_tire_size_rejects_garbage():
    with pytest.raises(ValueError):
        normalize_tire_size("225-45-18")


def test_normalize_thread():
    assert normalize_thread("m14 × 1,5") == "M14x1.5"
