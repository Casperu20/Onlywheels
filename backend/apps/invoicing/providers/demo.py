"""
Mock invoice for demos and coursework (SMARTBILL_DEMO=True while SMARTBILL_ENABLED=False).

Nothing is sent to SmartBill or ANAF: the PDF imitates the usual layout of a Romanian invoice and is
stamped on every part as a demo that is not a fiscal document. Refused by production settings.
"""

import unicodedata
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from apps.orders.models import Order

DEMO_SERIES = "DEMO"
CENT = Decimal("0.01")
PAGE_WIDTH, PAGE_HEIGHT = 595, 842
LEFT, RIGHT = 40, 555

# Standard Helvetica / Helvetica-Bold advance widths (1/1000 em) for printable ASCII 32..126.
_ASCII = [chr(code) for code in range(32, 127)]
_WIDTHS = dict(
    zip(
        _ASCII,
        [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278]
        + [556] * 10
        + [278, 278, 584, 584, 584, 556, 1015]
        + [667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833]
        + [722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611]
        + [278, 278, 278, 469, 556, 333]
        + [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833]
        + [556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500]
        + [334, 260, 334, 584],
        strict=True,
    )
)
_BOLD_WIDTHS = dict(
    zip(
        _ASCII,
        [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278]
        + [556] * 10
        + [333, 333, 584, 584, 584, 611, 975]
        + [722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833]
        + [722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611]
        + [333, 278, 333, 584, 556, 333]
        + [556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889]
        + [611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500]
        + [389, 280, 389, 584],
        strict=True,
    )
)
_TRANSLATE = str.maketrans({"×": "x", "·": "-", "–": "-", "—": "-", "„": '"', "”": '"', "“": '"', "’": "'"})


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value).translate(_TRANSLATE))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return plain.encode("ascii", "replace").decode()


def _escape(value: str) -> str:
    return _fold(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _money(value: Decimal) -> str:
    whole, _, cents = f"{value.quantize(CENT, ROUND_HALF_UP):,.2f}".partition(".")
    return f"{whole.replace(',', '.')},{cents}"


def _width(value: str, size: float, bold: bool = False) -> float:
    widths = _BOLD_WIDTHS if bold else _WIDTHS
    return sum(widths.get(char, 556) for char in _fold(value)) * size / 1000


def _clip(value: str, limit: int) -> str:
    value = _fold(value)
    return value if len(value) <= limit else value[: limit - 3] + "..."


class _Canvas:
    def __init__(self) -> None:
        self.ops: list[str] = []

    def text(self, x: float, y: float, value: str, *, size: float = 9, bold: bool = False, gray: float = 0) -> None:
        font = "F2" if bold else "F1"
        self.ops.append(f"{gray} g BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({_escape(value)}) Tj ET")

    def right(self, x: float, y: float, value: str, *, size: float = 9, bold: bool = False) -> None:
        self.text(x - _width(value, size, bold), y, value, size=size, bold=bold)

    def rect(self, x: float, y: float, w: float, h: float, rgb: tuple[float, float, float]) -> None:
        self.ops.append(f"{rgb[0]} {rgb[1]} {rgb[2]} rg {x} {y} {w} {h} re f")

    def line(self, x1: float, y1: float, x2: float, y2: float, gray: float = 0.75) -> None:
        self.ops.append(f"{gray} G 0.6 w {x1} {y1} m {x2} {y2} l S")

    def watermark(self, value: str) -> None:
        self.ops.append(f"q 0.94 g BT /F2 130 Tf 0.766 0.643 -0.643 0.766 150 230 Tm ({_escape(value)}) Tj ET Q")


def _net_and_vat(gross: Decimal, rate: Decimal) -> tuple[Decimal, Decimal]:
    vat = (gross * rate / (1 + rate)).quantize(CENT, ROUND_HALF_UP)
    return gross - vat, vat


def _lines(order: Order) -> list[tuple[str, str, str, str, Decimal, Decimal]]:
    """(name, detail, code, unit, quantity, gross line value) in SmartBill order: products, discount, services."""
    rows = [
        (item.product_name, item.description, item.sku, "buc", Decimal(item.quantity), item.line_total)
        for item in order.items.order_by("created_at")
    ]
    if order.discount:
        detail = f"Voucher {order.voucher_code}" if order.voucher_code else ""
        rows.append(("Discount", detail, "", "buc", Decimal(1), -order.discount))
    for name, amount in (("Transport", order.shipping), ("Montaj la service partener", order.fitting)):
        if amount:
            rows.append((name, "", "", "serv", Decimal(1), amount))
    return rows


def demo_invoice_pdf(order: Order, *, number: str, issued_at: datetime) -> bytes:
    rate = Decimal(settings.VAT_RATE)
    percent = f"{(rate * 100).normalize():f}%"
    canvas = _Canvas()
    canvas.watermark("DEMO")

    # Supplier (left) and document header (right).
    canvas.text(LEFT, 790, "OnlyWheels SRL (demo)", size=13, bold=True)
    for offset, value in enumerate(
        (
            "CIF: RO00000000 (fictiv)",
            "Reg. Com.: J00/0000/2026 (fictiv)",
            "Cluj-Napoca, Romania",
            "contact@onlywheels.ro",
        )
    ):
        canvas.text(LEFT, 774 - offset * 12, value, size=8.5, gray=0.3)
    canvas.right(RIGHT, 788, "FACTURA", size=22, bold=True)
    canvas.right(RIGHT, 770, f"Seria {DEMO_SERIES} nr. {number}", size=10, bold=True)
    canvas.right(RIGHT, 756, f"Data emiterii: {issued_at:%d.%m.%Y}", size=9)
    canvas.right(RIGHT, 744, f"Comanda: {order.number}", size=9)
    canvas.right(RIGHT, 732, f"Cota TVA: {percent}", size=9)

    # Demo banner.
    canvas.rect(LEFT, 676, RIGHT - LEFT, 40, (0.86, 0.15, 0.15))
    canvas.text(
        LEFT + 12, 701, "MACHETA DEMO - API-ul oficial SmartBill este dezactivat momentan.", size=10, bold=True, gray=1
    )
    canvas.text(
        LEFT + 12,
        686,
        "NU ESTE DOCUMENT FISCAL. Nu a fost emis prin SmartBill si nu a fost transmis in e-Factura (ANAF).",
        size=8,
        gray=1,
    )

    # Client.
    canvas.text(LEFT, 652, "CLIENT", size=8, bold=True, gray=0.45)
    canvas.text(LEFT, 638, order.full_name, size=10.5, bold=True)
    address = ", ".join(part for part in (order.line1, order.line2) if part)
    for offset, value in enumerate(
        (address, f"{order.city}, jud. {order.county}, {order.postal_code}, {order.country}", order.email, order.phone)
    ):
        canvas.text(LEFT, 625 - offset * 11, _clip(value, 90), size=8.5, gray=0.25)

    # Lines table.
    columns = {"nr": LEFT + 6, "name": LEFT + 26, "um": 318, "qty": 375, "price": 440, "value": 500, "vat": RIGHT - 6}
    top = 568
    canvas.rect(LEFT, top - 6, RIGHT - LEFT, 20, (0.93, 0.94, 0.96))
    canvas.text(columns["nr"], top, "Nr.", size=7.5, bold=True)
    canvas.text(columns["name"], top, "Denumire produs / serviciu", size=7.5, bold=True)
    canvas.text(columns["um"], top, "U.M.", size=7.5, bold=True)
    canvas.right(columns["qty"], top, "Cant.", size=7.5, bold=True)
    canvas.right(columns["price"], top, "Pret fara TVA", size=7.5, bold=True)
    canvas.right(columns["value"], top, "Valoare", size=7.5, bold=True)
    canvas.right(columns["vat"], top, f"TVA {percent}", size=7.5, bold=True)

    y = top - 24
    rows = _lines(order)
    for index, (name, detail, code, unit, quantity, gross) in enumerate(rows, start=1):
        if y < 190:
            canvas.text(
                columns["name"], y, f"... inca {len(rows) - index + 1} pozitii, incluse in total", size=8, gray=0.4
            )
            y -= 22
            break
        net, vat = _net_and_vat(gross, rate)
        unit_net = (net / quantity).quantize(CENT, ROUND_HALF_UP)
        canvas.text(columns["nr"], y, str(index), size=8.5)
        canvas.text(columns["name"], y, _clip(name, 48), size=8.5, bold=True)
        canvas.text(columns["um"], y, unit, size=8.5)
        canvas.right(columns["qty"], y, f"{quantity.normalize():f}", size=8.5)
        canvas.right(columns["price"], y, _money(unit_net), size=8.5)
        canvas.right(columns["value"], y, _money(net), size=8.5)
        canvas.right(columns["vat"], y, _money(vat), size=8.5)
        extra = " - ".join(part for part in (code and f"Cod: {code}", detail) if part)
        if extra:
            canvas.text(columns["name"], y - 10, _clip(extra, 60), size=7, gray=0.45)
            y -= 10
        canvas.line(LEFT, y - 7, RIGHT, y - 7)
        y -= 22

    # Totals.
    net_total = order.total - order.vat
    y -= 6
    for label, value, bold in (
        ("Total fara TVA", net_total, False),
        (f"TVA {percent}", order.vat, False),
        (f"TOTAL DE PLATA ({order.currency})", order.total, True),
    ):
        size = 11 if bold else 9
        canvas.right(440, y, label, size=size, bold=bold)
        canvas.right(columns["vat"], y, _money(value), size=size, bold=bold)
        y -= 16 if bold else 14
    payment = f"Achitat online la {order.paid_at:%d.%m.%Y}" if order.paid_at else "Plata online"
    canvas.text(LEFT, y + 30, payment, size=8.5, gray=0.3)

    # Footer.
    canvas.line(LEFT, 70, RIGHT, 70)
    canvas.text(
        LEFT,
        56,
        "Macheta generata de OnlyWheels in formatul unei facturi SmartBill, pentru prezentare.",
        size=7.5,
        gray=0.4,
    )
    canvas.text(
        LEFT,
        45,
        "Factura reala se emite automat prin SmartBill dupa configurarea contului (SMARTBILL_ENABLED).",
        size=7.5,
        gray=0.4,
    )
    return _pdf("\n".join(canvas.ops).encode("latin-1"))


def _pdf(stream: bytes) -> bytes:
    fonts = b"/Font << /F1 5 0 R /F2 6 0 R >>"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << %s >> /Contents 4 0 R >>"
        % (PAGE_WIDTH, PAGE_HEIGHT, fonts),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)
