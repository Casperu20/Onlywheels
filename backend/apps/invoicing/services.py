"""Issue and store SmartBill invoices after a confirmed payment."""

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.orders.models import Order

from .models import Invoice
from .providers import (
    SmartBillAmbiguousError,
    SmartBillConfigurationError,
    SmartBillPDFError,
    SmartBillProvider,
    SmartBillRejectedError,
)
from .providers.demo import DEMO_SERIES, demo_invoice_pdf


def _issue_demo_invoice(invoice: Invoice, order: Order) -> Invoice:
    """Mock invoice while SmartBill is disabled (SMARTBILL_DEMO); never sent to SmartBill or ANAF."""
    issued_at = timezone.now()
    number = order.number[:20]
    invoice.provider = "demo"
    invoice.series = DEMO_SERIES
    invoice.number = number
    invoice.issued_at = issued_at
    invoice.total = order.total
    invoice.pdf.save(
        f"{slugify(f'{DEMO_SERIES}-{number}')}.pdf",
        ContentFile(demo_invoice_pdf(order, number=number, issued_at=issued_at)),
        save=False,
    )
    invoice.status = Invoice.Status.ISSUED
    invoice.last_error = ""
    invoice.save(
        update_fields=[
            "provider",
            "series",
            "number",
            "issued_at",
            "total",
            "pdf",
            "status",
            "last_error",
            "updated_at",
        ]
    )
    return invoice


def issue_invoice(order: Order) -> Invoice:
    invoice, _ = Invoice.objects.get_or_create(
        order=order,
        defaults={"total": order.total, "status": Invoice.Status.PENDING},
    )
    provider = SmartBillProvider()

    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if invoice.status in (
            Invoice.Status.ISSUED,
            Invoice.Status.ISSUING,
            Invoice.Status.REVIEW_REQUIRED,
        ):
            return invoice
        if invoice.status == Invoice.Status.PDF_PENDING:
            action = "download_pdf"
        else:
            if not settings.SMARTBILL_ENABLED:
                if settings.SMARTBILL_DEMO:
                    return _issue_demo_invoice(invoice, order)
                invoice.status = Invoice.Status.FAILED
                invoice.last_error = "SmartBill invoicing is disabled."
                invoice.save(update_fields=["status", "last_error", "updated_at"])
                return invoice
            invoice.status = Invoice.Status.ISSUING
            invoice.attempt_count += 1
            invoice.last_attempted_at = timezone.now()
            invoice.last_error = ""
            invoice.save(
                update_fields=[
                    "status",
                    "attempt_count",
                    "last_attempted_at",
                    "last_error",
                    "updated_at",
                ]
            )
            action = "issue"

    if action == "issue":
        try:
            result = provider.issue(order, reference=order.number)
        except (SmartBillConfigurationError, SmartBillRejectedError) as exc:
            invoice.status = Invoice.Status.FAILED
            invoice.last_error = str(exc)[:1000]
            invoice.save(update_fields=["status", "last_error", "updated_at"])
            return invoice
        except SmartBillAmbiguousError as exc:
            invoice.status = Invoice.Status.REVIEW_REQUIRED
            invoice.last_error = str(exc)[:1000]
            invoice.save(update_fields=["status", "last_error", "updated_at"])
            return invoice

        invoice.series = result.series
        invoice.number = result.number
        invoice.provider_reference = result.document_id
        invoice.issued_at = result.issued_at
        invoice.total = result.total
        invoice.status = Invoice.Status.PDF_PENDING
        invoice.save(
            update_fields=[
                "series",
                "number",
                "provider_reference",
                "issued_at",
                "total",
                "status",
                "updated_at",
            ]
        )

    try:
        pdf = provider.download_pdf(series=invoice.series, number=invoice.number)
    except (SmartBillConfigurationError, SmartBillPDFError) as exc:
        invoice.last_error = str(exc)[:1000]
        invoice.save(update_fields=["last_error", "updated_at"])
        return invoice

    filename = f"{slugify(f'{invoice.series}-{invoice.number}') or 'invoice'}.pdf"
    invoice.pdf.save(filename, ContentFile(pdf), save=False)
    invoice.status = Invoice.Status.ISSUED
    invoice.last_error = ""
    invoice.save(update_fields=["pdf", "status", "last_error", "updated_at"])
    return invoice
