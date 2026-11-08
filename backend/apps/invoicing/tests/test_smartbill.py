from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.invoicing.models import Invoice
from apps.invoicing.services import issue_invoice
from apps.orders.models import OrderItem
from tests.factories import make_order

pytestmark = pytest.mark.django_db

API_BASE = "https://ws.smartbill.ro/SBORO/api"
PDF_BYTES = b"%PDF-1.7\nOnlyWheels invoice\n"
INVOICE_URL = "/api/v1/invoices/"


@pytest.fixture
def smartbill_settings(settings, tmp_path):
    settings.SMARTBILL_ENABLED = True
    settings.SMARTBILL_API_BASE_URL = API_BASE
    settings.SMARTBILL_USER = "merchant@example.test"
    settings.SMARTBILL_TOKEN = "test-token"
    settings.SMARTBILL_CIF = "RO123456"
    settings.SMARTBILL_SERIES = "TEST"
    settings.SMARTBILL_TAX_NAME = "Test VAT"
    settings.SMARTBILL_MEASURING_UNIT = "buc"
    settings.PRIVATE_INVOICE_ROOT = tmp_path
    settings.VAT_RATE = Decimal("0.21")
    return settings


@pytest.fixture
def order_with_item(user):
    order = make_order(user, total=Decimal("100.00"), subtotal=Decimal("100.00"))
    OrderItem.objects.create(
        order=order,
        product_name="Forged wheel",
        product_type="wheel",
        sku="WH-001",
        unit_price=Decimal("100.00"),
        quantity=1,
        line_total=Decimal("100.00"),
    )
    return order


def _response(*, body=None, content=b"", status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = body
    response.content = content
    response.headers = {"Content-Type": "application/octet-stream"}
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status_code}")
    return response


def _successful_issue_response():
    return _response(
        body={
            "errorText": "",
            "message": "",
            "series": "TEST",
            "number": "1001",
            "documentId": 501,
            "documentViewUrl": "https://cloud.smartbill.ro/documente/extern/invoice/501",
        }
    )


def test_issue_invoice_persists_smartbill_metadata_and_private_pdf(order_with_item, smartbill_settings):
    with (
        patch("requests.post", return_value=_successful_issue_response()) as post,
        patch("requests.get", return_value=_response(content=PDF_BYTES)) as get,
    ):
        invoice = issue_invoice(order_with_item)

    invoice.refresh_from_db()
    assert invoice.status == "issued"
    assert (invoice.series, invoice.number, invoice.total) == (
        "TEST",
        "1001",
        Decimal("100.00"),
    )
    assert invoice.provider_reference == "501"
    assert invoice.efactura_status == Invoice.EFacturaStatus.NOT_SENT
    with invoice.pdf.open("rb") as pdf:
        assert pdf.read() == PDF_BYTES
    with pytest.raises(ValueError, match="not accessible via a URL"):
        str(invoice.pdf.url)

    request = post.call_args.kwargs
    assert post.call_args.args == (f"{API_BASE}/invoice/v2",)
    assert request["auth"] == ("merchant@example.test", "test-token")
    assert request["json"]["companyVatCode"] == "RO123456"
    assert request["json"]["seriesName"] == "TEST"
    assert request["json"]["client"] == {
        "name": "Ana Pop",
        "country": "RO",
        "address": "Str. Exemplu 1",
        "city": "Cluj-Napoca",
        "county": "Cluj",
        "email": order_with_item.email,
        "phone": "0712345678",
    }
    assert request["json"]["products"] == [
        {
            "name": "Forged wheel",
            "code": "WH-001",
            "quantity": 1,
            "price": 100.0,
            "measuringUnitName": "buc",
            "taxName": "Test VAT",
            "taxPercentage": 21,
            "isTaxIncluded": True,
        }
    ]
    assert order_with_item.number in request["json"]["observations"]
    assert get.call_args.args == (f"{API_BASE}/invoice/pdf",)
    assert get.call_args.kwargs["params"] == {
        "cif": "RO123456",
        "seriesname": "TEST",
        "number": "1001",
    }
    assert get.call_args.kwargs["headers"] == {"Accept": "application/octet-stream"}


def test_reissuing_an_issued_order_does_not_create_another_invoice(order_with_item, smartbill_settings):
    with (
        patch("requests.post", return_value=_successful_issue_response()) as post,
        patch("requests.get", return_value=_response(content=PDF_BYTES)) as get,
    ):
        first = issue_invoice(order_with_item)
        second = issue_invoice(order_with_item)

    assert first.pk == second.pk
    post.assert_called_once()
    get.assert_called_once()


def test_invoice_details_and_pdf_are_available_only_to_owner_and_staff(
    auth_client, user, order_with_item, smartbill_settings
):
    with (
        patch("requests.post", return_value=_successful_issue_response()),
        patch("requests.get", return_value=_response(content=PDF_BYTES)),
    ):
        invoice = issue_invoice(order_with_item)

    details_url = f"{INVOICE_URL}{order_with_item.number}/"
    pdf_url = f"{details_url}pdf/"
    owner_response = auth_client.get(details_url)
    assert owner_response.status_code == 200
    assert owner_response.json()["status"] == Invoice.Status.ISSUED
    assert owner_response.json()["pdf_url"] == pdf_url
    order_response = auth_client.get(f"/api/v1/orders/{order_with_item.number}/")
    assert order_response.status_code == 200
    assert order_response.json()["invoice"]["status"] == Invoice.Status.ISSUED
    assert order_response.json()["invoice"]["pdf_url"] == pdf_url
    owner_pdf = auth_client.get(pdf_url)
    assert owner_pdf.status_code == 200
    assert b"".join(owner_pdf.streaming_content) == PDF_BYTES

    anonymous_client = APIClient()
    assert anonymous_client.get(details_url).status_code == 401

    other_user = User.objects.create_user(email="other@example.test", password="test-pass")
    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    assert other_client.get(details_url).status_code == 404
    assert other_client.get(pdf_url).status_code == 404

    staff_user = User.objects.create_user(email="staff@example.test", password="test-pass", is_staff=True)
    staff_client = APIClient()
    staff_client.force_authenticate(user=staff_user)
    assert staff_client.get(details_url).status_code == 200
    assert staff_client.get(pdf_url).status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED


@pytest.mark.parametrize(
    ("initial_status", "initial_attempts"),
    ((Invoice.Status.PENDING, 0), (Invoice.Status.FAILED, 1)),
)
def test_staff_can_retry_a_pending_or_failed_invoice_from_admin(
    order_with_item, smartbill_settings, initial_status, initial_attempts
):
    invoice = Invoice.objects.create(
        order=order_with_item,
        total=order_with_item.total,
        status=initial_status,
        attempt_count=initial_attempts,
        last_error="Temporary SmartBill error",
    )
    staff_user = User.objects.create_superuser(email="admin@example.test", password="test-pass")
    admin_client = Client()
    admin_client.force_login(staff_user)

    with (
        patch("requests.post", return_value=_successful_issue_response()),
        patch("requests.get", return_value=_response(content=PDF_BYTES)),
    ):
        response = admin_client.post(
            reverse("admin:invoicing_invoice_changelist"),
            {"action": "retry_failed_invoices", "_selected_action": [str(invoice.pk)]},
            follow=True,
        )

    assert response.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.ISSUED
    assert invoice.attempt_count == initial_attempts + 1
    assert invoice.last_error == ""


def test_staff_can_mark_only_stale_issuing_invoices_for_manual_review(user, order_with_item):
    stale = Invoice.objects.create(
        order=order_with_item,
        total=order_with_item.total,
        status=Invoice.Status.ISSUING,
        attempt_count=1,
        last_attempted_at=timezone.now() - timedelta(minutes=31),
    )
    recent_order = make_order(user, total=order_with_item.total)
    recent = Invoice.objects.create(
        order=recent_order,
        total=recent_order.total,
        status=Invoice.Status.ISSUING,
        attempt_count=1,
        last_attempted_at=timezone.now() - timedelta(minutes=5),
    )
    staff_user = User.objects.create_superuser(email="admin@example.test", password="test-pass")
    admin_client = Client()
    admin_client.force_login(staff_user)

    response = admin_client.post(
        reverse("admin:invoicing_invoice_changelist"),
        {
            "action": "mark_stale_issues_for_review",
            "_selected_action": [str(stale.pk), str(recent.pk)],
        },
        follow=True,
    )

    assert response.status_code == 200
    stale.refresh_from_db()
    recent.refresh_from_db()
    assert stale.status == Invoice.Status.REVIEW_REQUIRED
    assert "reconcile" in stale.last_error.lower()
    assert recent.status == Invoice.Status.ISSUING


def test_invoice_payload_preserves_order_discount_and_shipping(order_with_item, smartbill_settings):
    item = order_with_item.items.get()
    item.quantity = 2
    item.line_total = Decimal("200.00")
    item.save(update_fields=["quantity", "line_total"])
    order_with_item.subtotal = Decimal("200.00")
    order_with_item.discount = Decimal("20.00")
    order_with_item.shipping = Decimal("25.00")
    order_with_item.total = Decimal("205.00")
    order_with_item.save(update_fields=["subtotal", "discount", "shipping", "total"])

    with (
        patch("requests.post", return_value=_successful_issue_response()) as post,
        patch("requests.get", return_value=_response(content=PDF_BYTES)),
    ):
        issue_invoice(order_with_item)

    assert post.call_args.kwargs["json"]["products"] == [
        {
            "name": "Forged wheel",
            "code": "WH-001",
            "quantity": 2,
            "price": 100.0,
            "measuringUnitName": "buc",
            "taxName": "Test VAT",
            "taxPercentage": 21,
            "isTaxIncluded": True,
        },
        {
            "name": "Order discount",
            "quantity": 1,
            "price": 0.0,
            "measuringUnitName": "buc",
            "taxName": "Test VAT",
            "taxPercentage": 21,
            "isTaxIncluded": True,
            "isDiscount": True,
            "discountType": 1,
            "discountValue": -20.0,
            "numberOfItems": 1,
        },
        {
            "name": "Shipping",
            "quantity": 1,
            "price": 25.0,
            "measuringUnitName": "buc",
            "taxName": "Test VAT",
            "taxPercentage": 21,
            "isTaxIncluded": True,
            "isService": True,
        },
    ]


def test_disabled_smartbill_records_retryable_failure_without_provider_call(order_with_item, smartbill_settings):
    smartbill_settings.SMARTBILL_ENABLED = False

    with patch("requests.post") as post, patch("requests.get") as get:
        invoice = issue_invoice(order_with_item)

    assert invoice.status == "failed"
    assert "disabled" in invoice.last_error.lower()
    post.assert_not_called()
    get.assert_not_called()


def test_missing_smartbill_configuration_fails_without_provider_call(order_with_item, smartbill_settings):
    smartbill_settings.SMARTBILL_TOKEN = ""

    with patch("requests.post") as post, patch("requests.get") as get:
        invoice = issue_invoice(order_with_item)

    assert invoice.status == "failed"
    assert invoice.last_error
    post.assert_not_called()
    get.assert_not_called()


def test_smartbill_rejection_is_visible_and_can_be_retried(order_with_item, smartbill_settings):
    rejected = _response(body={"errorText": "The invoice series was not found."}, status_code=422)
    with (
        patch("requests.post", side_effect=[rejected, _successful_issue_response()]) as post,
        patch("requests.get", return_value=_response(content=PDF_BYTES)),
    ):
        failed = issue_invoice(order_with_item)
        retried = issue_invoice(order_with_item)

    assert failed.status == "failed"
    assert "series was not found" in failed.last_error
    assert retried.status == "issued"
    assert post.call_count == 2


def test_ambiguous_timeout_requires_reconciliation_before_another_issue_attempt(order_with_item, smartbill_settings):
    with patch("requests.post", side_effect=requests.Timeout("response timed out")) as post:
        first = issue_invoice(order_with_item)
        second = issue_invoice(order_with_item)

    assert first.status == "review_required"
    assert second.status == "review_required"
    post.assert_called_once()


def test_malformed_success_response_is_not_reissued_automatically(order_with_item, smartbill_settings):
    malformed = _response(body={"errorText": "", "series": "TEST"})
    with patch("requests.post", return_value=malformed) as post:
        first = issue_invoice(order_with_item)
        second = issue_invoice(order_with_item)

    assert first.status == "review_required"
    assert second.status == "review_required"
    post.assert_called_once()


def test_pdf_failure_retries_download_without_creating_a_second_invoice(order_with_item, smartbill_settings):
    invalid_pdf = _response(content=b"not a pdf")
    with (
        patch("requests.post", return_value=_successful_issue_response()) as post,
        patch(
            "requests.get",
            side_effect=[invalid_pdf, _response(content=PDF_BYTES)],
        ) as get,
    ):
        first = issue_invoice(order_with_item)
        second = issue_invoice(order_with_item)

    assert first.status == "pdf_pending"
    assert second.status == "issued"
    assert second.provider_reference == "501"
    post.assert_called_once()
    assert get.call_count == 2
