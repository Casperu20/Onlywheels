# Netopia Sandbox Payments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real Netopia sandbox checkout and installment-capable callback flow without changing the existing Stripe or development fake-payment behavior.

**Architecture:** Implement Netopia as a `PaymentProvider`, selected explicitly by Django settings. Treat the signed server callback—not the browser redirect—as payment authority; validate the stored order amount/currency and process each provider event idempotently through the existing payment and order services.

**Tech Stack:** Django 5, DRF, existing `requests` dependency, pytest-django, Netopia hosted checkout API.

**Spec:** [2026-11-08-phase-2-sandbox-design.md](../specs/2026-11-08-phase-2-sandbox-design.md)

## Global Constraints

- Never store secrets in frontend build variables, database fixtures, tests, or documentation examples.
- Do not silently substitute fake provider behavior when a real adapter is misconfigured or a provider request fails.
- Mock external HTTP calls in automated tests.
- A real sandbox run requires user-configured provider-issued credentials; no credential is to be sent in chat or committed.
- Backend commands below run from `backend/`; they require the documented `.env`, Python >=3.12, and a configured database.

## Review Focus

- Invalid callback authentication must not change payment/order state — test bad/missing signature.
- Correctly authenticated but mismatched amount/currency must not mark the order paid — test both mismatches.
- Replayed and out-of-order callback events must not duplicate state transitions — test duplicate and terminal-state delivery.
- Provider timeout/error must fail visibly and must not create a success-shaped checkout — test HTTP error and timeout.
- Existing Stripe/fake behavior must remain intact — run the complete payments tests.

---

### Task 0: Bootstrap the missing backend baseline

**Files:**
- Create: `backend/uv.lock`
- Create initial migrations: `backend/apps/*/migrations/0001_initial.py`

- [x] **Step 1: Prepare the development environment** using [SETUP.md §3](../../SETUP.md#3-backend-django): run `uv sync` and generate initial migrations for all current apps with `uv run python manage.py makemigrations`. Used an ephemeral SQLite URL and test-only key instead of creating `.env`; no local credentials were available.
- [x] **Step 2: Run** `uv run python manage.py migrate` and `uv run python manage.py seed_demo`; confirm all current migrations apply and demo setup completes.
- [x] **Step 3: Run the baseline backend checks** from `backend/`: `uv run ruff check .`, `uv run python manage.py makemigrations --check --dry-run`, and `uv run pytest`.
- [x] **Step 4: Continue with feature migrations only after this baseline is clean.** This prerequisite is shared by the remaining backend plans.

### Task 1: Netopia checkout adapter and configuration

**Files:**
- Create/modify: `backend/apps/payments/providers/netopia.py`
- Modify: `backend/apps/payments/providers/__init__.py`
- Modify: `backend/config/settings/base.py`
- Modify: `backend/.env.example`
- Test: `backend/apps/payments/tests/test_payments.py`

**Interfaces:**
- Consumes: `PaymentProvider.create_checkout(order: Order) -> CheckoutSession`.
- Produces: `NetopiaProvider.create_checkout(order: Order) -> CheckoutSession`; `get_provider()` resolves `PAYMENT_PROVIDER="netopia"`.

- [x] **Step 1: Write failing adapter tests** for the sandbox request, successful hosted-checkout URL/session mapping, malformed response, timeout, and provider error; assert credentials and sandbox mode are selected from settings.
- [x] **Step 2: Run the focused tests** with `uv run pytest apps/payments/tests/test_payments.py -k netopia -q`; confirm the new cases fail before implementation.
- [x] **Step 3: Verify the current official Netopia API contract** for sandbox base URL, checkout fields, auth, currency units, callback signature, and installment support. Implement the adapter with the existing `requests` dependency; use explicit `NETOPIA_MODE=sandbox|live` and Netopia merchant credentials in settings and `.env.example`.
- [x] **Step 4: Run focused tests**; assert only documented provider responses are accepted and provider failures raise an explicit payment error.
- [x] **Step 5: Run all payment tests** with `uv run pytest apps/payments/tests/test_payments.py -q`; preserve the fake and Stripe cases.

### Task 2: Signed callback and installment state

**Files:**
- Modify: `backend/apps/payments/views.py`
- Modify: `backend/apps/payments/urls.py`
- Modify: `backend/apps/payments/services.py`
- Modify: `backend/apps/payments/models.py`
- Create migration: `backend/apps/payments/migrations/`
- Test: `backend/apps/payments/tests/test_payments.py`

**Interfaces:**
- Consumes: Task 1 `NetopiaProvider`; existing `Payment`, `WebhookEvent`, and `orders.services.mark_paid`.
- Produces: `verify_netopia_callback(payload: bytes, headers: Mapping[str, str]) -> dict`; `handle_netopia_event(event: dict) -> None`; `POST /api/v1/payments/webhook/netopia/`.

- [x] **Step 1: Write failing webhook tests** for valid success, rejected signature, amount/currency mismatch, failed/cancelled events, duplicate event ID, and installment data mapping into the payment record.
- [x] **Step 2: Run** `uv run pytest apps/payments/tests/test_payments.py -k netopia_webhook -q`; confirm the new cases fail.
- [x] **Step 3: Implement** callback parsing and signature verification exactly as documented by Netopia; record provider event IDs using the existing unique constraint; validate the stored payment amount/currency before updating status; call `mark_paid` only for authenticated successful events. Add only the installment field(s) required by the callback contract and generate a migration.
- [x] **Step 4: Run focused webhook tests**; assert the browser redirect cannot mark an order paid and retries call `mark_paid` once.
- [x] **Step 5: Run all payment and order lifecycle tests** with `uv run pytest apps/payments/tests apps/orders/tests -q`.

### Task 3: Sandbox setup and manual verification

**Files:**
- Modify: `docs/SETUP.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `docs/ROADMAP.md`

- [x] **Step 1: Document** sandbox account setup, exact environment variables, callback URL/tunnel requirement, test payment path, installment limitations, and the explicit production-mode switch.
- [x] **Step 2: Verify documentation** against the implemented settings and the official Netopia sandbox contract; include no live values or secrets.
- [x] **Step 3: Run the payment test suite** and record a manual sandbox checklist. Mark real-provider verification pending until credentials are configured locally.

> The workspace currently has no Git repository; commit each independently tested task after Git is initialized.
