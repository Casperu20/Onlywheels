import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.invoicing.models import Invoice
from apps.invoicing.services import issue_invoice
from apps.orders.models import OrderItem
from tests.factories import make_order

pytestmark = pytest.mark.django_db

BACKEND_DIR = Path(__file__).resolve().parents[3]


@pytest.fixture
def demo_settings(settings, tmp_path):
    settings.SMARTBILL_ENABLED = False
    settings.SMARTBILL_DEMO = True
    settings.PRIVATE_INVOICE_ROOT = tmp_path
    settings.VAT_RATE = Decimal("0.21")
    return settings


@pytest.fixture
def demo_order(user):
    order = make_order(
        user,
        subtotal=Decimal("900.00"),
        discount=Decimal("20.00"),
        shipping=Decimal("25.00"),
        total=Decimal("905.00"),
        vat=Decimal("157.07"),
    )
    OrderItem.objects.create(
        order=order,
        product_name='Vossen HF-5 19" Argintiu',
        product_type="wheel",
        sku="VOS-HF5-19",
        unit_price=Decimal("225.00"),
        quantity=4,
        line_total=Decimal("900.00"),
    )
    return order


def test_disabled_smartbill_in_demo_mode_issues_a_marked_mock_invoice_without_provider_calls(demo_order, demo_settings):
    with patch("requests.post") as post, patch("requests.get") as get:
        invoice = issue_invoice(demo_order)

    invoice.refresh_from_db()
    post.assert_not_called()
    get.assert_not_called()
    assert invoice.status == Invoice.Status.ISSUED
    assert invoice.provider == "demo"
    assert (invoice.series, invoice.number) == ("DEMO", demo_order.number)
    assert invoice.total == Decimal("905.00")
    assert invoice.issued_at is not None
    assert invoice.efactura_status == Invoice.EFacturaStatus.NOT_SENT

    with invoice.pdf.open("rb") as handle:
        pdf = handle.read()
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.rstrip().endswith(b"%%EOF")
    for text in (
        b"FACTURA",
        b"DEMO",
        b"API-ul oficial SmartBill este dezactivat",
        b"NU ESTE DOCUMENT FISCAL",
        b'Vossen HF-5 19" Argintiu',
        b"Argintiu",
        b"VOS-HF5-19",
        b"Discount",
        b"Transport",
        b"905,00",
        demo_order.number.encode(),
    ):
        assert text in pdf, text


def test_demo_invoice_is_idempotent(demo_order, demo_settings):
    first = issue_invoice(demo_order)
    second = issue_invoice(demo_order)

    assert first.pk == second.pk
    assert Invoice.objects.filter(order=demo_order).count() == 1


def test_demo_invoice_folds_romanian_diacritics_for_the_builtin_pdf_font(user, demo_settings):
    order = make_order(user, full_name="Ștefan Țăran")
    OrderItem.objects.create(
        order=order,
        product_name="Jantă aliaj",
        product_type="wheel",
        sku="J-1",
        unit_price=Decimal("100.00"),
        quantity=1,
        line_total=Decimal("100.00"),
    )

    invoice = issue_invoice(order)

    with invoice.pdf.open("rb") as handle:
        pdf = handle.read()
    assert b"Stefan Taran" in pdf
    assert b"Janta aliaj" in pdf


def test_disabled_smartbill_without_demo_mode_still_records_failure(demo_order, demo_settings):
    demo_settings.SMARTBILL_DEMO = False

    invoice = issue_invoice(demo_order)

    assert invoice.status == Invoice.Status.FAILED
    assert invoice.provider == "smartbill"


def test_order_api_flags_demo_invoice_and_serves_its_pdf(demo_order, demo_settings, user):
    issue_invoice(demo_order)
    client = APIClient()
    client.force_authenticate(user)

    data = client.get(f"/api/v1/orders/{demo_order.number}/").json()
    assert data["invoice"]["is_demo"] is True
    assert data["invoice"]["pdf_url"]

    response = client.get(data["invoice"]["pdf_url"])
    assert response.status_code == 200
    assert b"".join(response.streaming_content).startswith(b"%PDF")


def test_production_settings_refuse_demo_invoices():
    env = {
        **os.environ,
        "SMARTBILL_DEMO": "True",
        "PAYMENT_PROVIDER": "stripe",
        "SHIPPING_CARRIER": "",
        "DJANGO_SECRET_KEY": "test-only",
        "DATABASE_URL": "sqlite:///:memory:",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings.prod"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "SMARTBILL_DEMO" in result.stderr
