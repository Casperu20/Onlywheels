# Courier Sandbox Shipping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and track Sameday or Fan Courier sandbox shipments for courier orders, while keeping garage-fitting orders out of the shipping workflow.

**Architecture:** Implement both `CarrierProvider` adapters and select one explicitly. On staff transition to processing, snapshot parcel weights, create one retry-safe shipment, and advance to shipped only after carrier success; poll and normalize tracking through Celery.

**Tech Stack:** Django 5, Celery, existing `requests` dependency, pytest-django, Sameday and Fan Courier APIs.

**Spec:** [2026-11-08-phase-2-sandbox-design.md](../specs/2026-11-08-phase-2-sandbox-design.md)

## Global Constraints

- Never store secrets in frontend build variables, database fixtures, tests, or documentation examples.
- Do not silently substitute fake provider behavior when a real adapter is misconfigured or a provider request fails.
- Mock external HTTP calls in automated tests.
- A real sandbox run requires user-configured provider-issued credentials; no credential is to be sent in chat or committed. _(Pending: needs carrier sandbox credentials.)_
- Use only explicit carrier credentials and configured sender/return addresses.
- Backend commands below run from `backend/`; complete the backend-baseline task in the Netopia plan first.

## Review Focus

- Garage-fitting orders must never create AWBs — test the transition for that delivery method.
- Missing/invalid item weight must not create a misleading label — test weight validation.
- Provider failure or timeout must not advance an order to shipped — test failure and retry.
- Repeated staff actions and webhook/task retries must not create duplicate shipments — test idempotency.
- Unknown or terminal tracking statuses must not regress state — test status normalization and monotonic updates.

---

### Task 1: Weight snapshots and shipment state

**Files:**
- Modify: `backend/apps/catalog/models.py`
- Modify: `backend/apps/catalog/admin.py`
- Modify: `backend/apps/orders/models.py`
- Modify: `backend/apps/orders/services.py`
- Modify: `backend/apps/shipping/models.py`
- Create migration: `backend/apps/catalog/migrations/`, `backend/apps/orders/migrations/`, `backend/apps/shipping/migrations/`
- Test: `backend/apps/shipping/tests/test_shipping.py`
- Test: `backend/apps/orders/tests/test_orders.py`
- Test: `backend/tests/factories.py`

**Interfaces:**
- Consumes: `ProductVariant`, order item snapshot creation, `Shipment`, `Order.Delivery`.
- Produces: validated `ProductVariant.shipping_weight_kg` and `OrderItem.shipping_weight_kg`; explicit pending/failed shipment state and provider error fields.

- [x] **Step 1: Write failing tests** for positive weight validation, copying weight to order items, seeded/factory weight values, shipment lifecycle state, and rejecting absent weight for courier fulfillment.
- [x] **Step 2: Run** `uv run pytest apps/shipping/tests/test_shipping.py apps/orders/tests/test_orders.py -k weight -q`; confirm the cases fail.
- [x] **Step 3: Implement** a positive decimal variant weight, immutable order-item weight snapshot, admin editing, and additive migrations. Add explicit pending/failed shipment state and bounded error text to `Shipment`.
- [x] **Step 4: Run** focused tests and `uv run python manage.py makemigrations --check --dry-run`.

### Task 2: Sameday and Fan Courier provider adapters

**Files:**
- Modify: `backend/apps/shipping/providers/base.py`
- Modify: `backend/apps/shipping/providers/sameday.py`
- Modify: `backend/apps/shipping/providers/fan_courier.py`
- Modify: `backend/apps/shipping/providers/__init__.py`
- Modify: `backend/config/settings/base.py`
- Modify: `backend/.env.example`
- Test: `backend/apps/shipping/tests/test_shipping.py`

**Interfaces:**
- Consumes: `CarrierProvider.create_awb(order, *, parcels, weight_kg) -> AwbResult`; `CarrierProvider.track(awb) -> str`.
- Produces: provider registry/config selection and normalized AWB/tracking behavior for both supported carriers.

- [x] **Step 1: Write failing HTTP-mocked tests** for each carrier's auth, AWB creation, label bytes, tracking URL, successful status mapping, rejected response, and token/API failure.
- [x] **Step 2: Run** `uv run pytest apps/shipping/tests/test_shipping.py -k provider -q`; confirm failure.
- [x] **Step 3: Verify official sandbox API contracts** for auth, endpoints, required sender/recipient/parcel fields, label format, tracking status values, and idempotency support. Implement both adapters with timeouts, safe error parsing, explicit `SHIPPING_CARRIER`, per-carrier sandbox/live configuration, and configured sender/return addresses.
- [x] **Step 4: Run provider tests**; assert no secret appears in logs or surfaced error messages and every mapped status is a `Shipment.Status`.

### Task 3: Order transitions, tracking worker, and customer view

**Files:**
- Create: `backend/apps/shipping/tasks.py`
- Modify: `backend/apps/orders/services.py`
- Modify: `backend/apps/orders/serializers.py`
- Modify: `backend/apps/shipping/admin.py`
- Modify: `backend/config/celery.py`
- Modify: `frontend/src/features/orders/api.ts`
- Modify: `frontend/src/routes/OrderPages.tsx`
- Modify: `frontend/src/i18n/locales/ro/common.json`
- Modify: `frontend/src/i18n/locales/en/common.json`
- Test: `backend/apps/shipping/tests/test_shipping.py`
- Test: `frontend/tests/unit/OrderDetailPage.test.tsx`

**Interfaces:**
- Consumes: Task 1 shipment state and Task 2 carrier registry; existing `change_status(order, new_status, *, by, note)`.
- Produces: `create_shipment_task(order_id: str)` and `refresh_shipment_task(shipment_id: str)`; order detail includes shipment status/tracking metadata.

- [x] **Step 1: Write failing tests** for processing transition scheduling, successful AWB then shipped state, carrier failure not shipped, garage-fit exclusion, idempotent repeated transition, and tracking status non-regression.
- [x] **Step 2: Run** focused backend tests and the new frontend test; confirm the new behaviors fail.
- [x] **Step 3: Implement** post-commit shipment task creation and hourly tracking; use carrier order-number references to reconcile retries. Expose the tracking URL and normalized status only on the owning order; retain admin visibility and retry action.
- [x] **Step 4: Run** `uv run pytest apps/shipping/tests apps/orders/tests -q` from `backend/`, then `pnpm exec vitest run tests/unit/OrderDetailPage.test.tsx`, `pnpm typecheck`, and `pnpm lint` from `frontend/`.

### Task 4: Sandbox operations documentation

**Files:**
- Modify: `backend/.env.example`
- Modify: `docs/SETUP.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `docs/ROADMAP.md`

- [x] **Step 1: Document** both carrier sandbox accounts/configuration, required product weights and sender addresses, Celery worker/tracking operation, failure recovery, and live-mode prerequisites.
- [x] **Step 2: Verify** documented settings match the code and run the complete shipping/order test suites.
- [ ] **Step 3: Run** one real sandbox AWB/tracking path when local credentials are configured; otherwise report that external validation as pending. _(Pending: needs carrier sandbox credentials.)_

> The workspace currently has no Git repository; commit each independently tested task after Git is initialized.
