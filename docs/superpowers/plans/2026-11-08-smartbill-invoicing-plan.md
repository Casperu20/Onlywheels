# SmartBill Sandbox Invoicing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue and expose one SmartBill test invoice per paid OnlyWheels order, with retryable provider errors and persisted PDF/e-Factura state.

**Architecture:** Call SmartBill through a small provider adapter from an on-commit Celery task triggered by the canonical paid-order transition. Persist pending/success/failure state so staff can observe and retry safely, and authorize customer access through the existing order ownership rules.

**Tech Stack:** Django 5, Celery, existing `requests` dependency, DRF, pytest-django, SmartBill API.

**Spec:** [2026-11-08-phase-2-sandbox-design.md](../specs/2026-11-08-phase-2-sandbox-design.md)

## Global Constraints

- Never store secrets in frontend build variables, database fixtures, tests, or documentation examples.
- Do not silently substitute fake provider behavior when a real adapter is misconfigured or a provider request fails.
- Mock external HTTP calls in automated tests.
- A real sandbox run requires user-configured provider-issued credentials; no credential is to be sent in chat or committed.
- Invoice, e-Factura, VAT, and retention behavior requires legal/accounting review before live use.
- Backend commands below run from `backend/`; complete the backend-baseline task in the Netopia plan first.

## Review Focus

- Duplicate `mark_paid` calls and Celery retries must not issue duplicate invoices — test repeated scheduling and worker retry.
- SmartBill timeout, rejection, or malformed response must leave a visible retryable error — test each provider failure.
- Order details and PDF download must not disclose another user's invoice — test owner, other user, and anonymous access.
- Missing company/provider configuration must fail explicitly without creating a fake invoice — test incomplete settings.
- PDF storage and e-Factura state must match provider results — test file bytes and each supported status.

---

### Task 1: SmartBill adapter and invoice lifecycle

**Files:**
- Create: `backend/apps/invoicing/providers/smartbill.py`
- Create: `backend/apps/invoicing/providers/__init__.py`
- Modify: `backend/apps/invoicing/services.py`
- Modify: `backend/apps/invoicing/models.py`
- Modify: `backend/config/settings/base.py`
- Modify: `backend/.env.example`
- Create migration: `backend/apps/invoicing/migrations/`
- Test: `backend/apps/invoicing/tests/test_smartbill.py`

**Interfaces:**
- Consumes: `Invoice`, `Order`, `requests`, and SmartBill's documented sandbox API.
- Produces: `SmartBillProvider.issue(order: Order, *, reference: str) -> SmartBillInvoiceResult`; `SmartBillProvider.download_pdf(reference: str) -> bytes`; `issue_invoice(order: Order) -> Invoice`.
- `SmartBillInvoiceResult` contains provider reference, series, number, issue timestamp, total, and optional normalized e-Factura status.

- [x] **Step 1: Write failing service tests** for successful invoice/PDF creation, repeated issue request, provider timeout/rejection, malformed response, and e-Factura status mapping.
- [x] **Step 2: Run** `uv run pytest apps/invoicing/tests/test_smartbill.py -q`; confirm the new tests fail.
- [x] **Step 3: Verify the official SmartBill V1 contract** for base URL, authentication, required company/customer/tax fields, invoice lookup/idempotency, PDF retrieval, and e-Factura status support. The API has no verified sandbox, invoice lookup/idempotency, or e-Factura status endpoint; keep issuance disabled by default, persist provider identifiers/PDF/error state, and place ambiguous outcomes in review-required.
- [x] **Step 4: Implement safe retries** using the order number as the stable external reference; do not automatically repeat ambiguous invoice creation. Do not mark an invoice successful until provider metadata and PDF handling succeed.
- [x] **Step 5: Run the invoice service tests**; assert one invoice per order and visible errors on all failure paths.

### Task 2: Paid-order task and authorized invoice access

**Files:**
- Create: `backend/apps/invoicing/urls.py`
- Create: `backend/apps/invoicing/views.py`
- Create: `backend/apps/invoicing/tasks.py`
- Modify: `backend/apps/orders/services.py`
- Modify: `backend/apps/orders/serializers.py`
- Modify: `backend/apps/orders/views.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/apps/invoicing/admin.py`
- Modify: `backend/config/celery.py`
- Modify: `frontend/src/features/orders/api.ts`
- Modify: `frontend/src/routes/OrderPages.tsx`
- Modify: `frontend/src/i18n/locales/en/common.json`
- Modify: `frontend/src/i18n/locales/ro/common.json`
- Test: `backend/apps/invoicing/tests/test_smartbill.py`
- Test: `backend/apps/orders/tests/test_orders.py`
- Test: `frontend/tests/unit/OrderInvoice.test.tsx`

**Interfaces:**
- Consumes: Task 1 `issue_invoice(order: Order) -> Invoice`; existing `mark_paid(order, *, note)`.
- Produces: `issue_invoice_task(order_id: str)`; `GET /api/v1/invoices/{order_number}/` for owner-authorized invoice metadata/PDF; staff retry through Admin.

- [x] **Step 1: Write failing tests** proving that `mark_paid` schedules exactly one invoice task after commit, a failed task is retryable, and invoice details/PDF are available only to the order owner and staff.
- [x] **Step 2: Run focused tests** with `uv run pytest apps/invoicing/tests/test_smartbill.py apps/orders/tests/test_orders.py -k invoice -q`; confirm failures.
- [x] **Step 3: Implement** on-commit task scheduling in the idempotent `mark_paid` path; persist a pending invoice in the payment transaction so broker enqueue failures remain recoverable, and log enqueue errors without undoing payment. Use Celery eager behavior in tests and the configured worker in deployment. Implement owner/staff-authorized metadata and PDF endpoints, staff retry for pending/failed/PDF-pending states, age-gated manual review for stale issuance, and customer order-page status/download.
- [x] **Step 4: Run** `uv run pytest apps/invoicing/tests/test_smartbill.py apps/orders/tests/test_orders.py -q`; verify no order state regression and no duplicate invoice on repeated payment events.

### Task 3: Configuration, manual sandbox run, and documentation

**Files:**
- Modify: `backend/config/celery.py`
- Modify: `backend/.env.example`
- Modify: `docs/SETUP.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `docs/ROADMAP.md`
- Modify: `infra/.env.prod.example`

- [x] **Step 1: Document** provider account setup, configuration, worker operation, customer/admin behavior, retry handling, and production/legal prerequisites.
- [x] **Step 2: Run** `uv run pytest apps/invoicing/tests apps/orders/tests -q` and verify Django's migration check.
- [x] **Step 3: Record the external-provider leg as pending** because no test account/credentials are configured; do not make a provider request.

> The workspace currently has no Git repository; commit each independently tested task after Git is initialized.
