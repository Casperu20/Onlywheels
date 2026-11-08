# AI Photo Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an authenticated AI photo-generation workflow with real Replicate/fal adapters, queued jobs, explicit usage/spend limits, private images, and a React experience.

**Architecture:** Validate and store customer uploads, reserve daily/user and global budget under a database transaction, enqueue a Celery task, and persist provider result/state. Expose owner-scoped API operations and a polling frontend; expire media after 30 days.

**Tech Stack:** Django 5, DRF, Celery, existing `requests` dependency, filesystem/S3-compatible storage, React, TypeScript, TanStack Query, pytest-django, Vitest.

**Spec:** [2026-11-08-phase-2-sandbox-design.md](../specs/2026-11-08-phase-2-sandbox-design.md)

## Global Constraints

- Never store secrets in frontend build variables, database fixtures, tests, or documentation examples.
- Do not silently substitute fake provider behavior when a real adapter is misconfigured or a provider request fails.
- Mock external HTTP calls in automated tests.
- Enforce five generations per user per day and a configurable USD 5/day whole-account estimated provider-spend ceiling.
- Delete uploaded input and result images after 30 days; owners can delete earlier.
- AI-generated images are illustrative and must not be represented as guaranteed product fit or exact wheel replacement.
- Backend commands below run from `backend/`; complete the backend-baseline task in the Netopia plan first.

## Review Focus

- Upload type, byte size, dimensions, and malformed image data must be rejected before provider use — test invalid and boundary uploads.
- Parallel requests must not overspend the global estimate or exceed a user's daily quota — test locked budget reservation.
- Failed/cancelled jobs must release reserved budget and not leak stack/provider secrets — test worker failure.
- Users must not read/delete another user's generations or media — test cross-user API access.
- Expired/user-deleted files must be removed from storage as well as the database — test storage deletion.

---

### Task 1: Provider interfaces, budget reservations, and safe upload API

**Files:**
- Modify: `backend/apps/ai_studio/models.py`
- Modify: `backend/apps/ai_studio/services.py`
- Create: `backend/apps/ai_studio/storage.py`
- Create: `backend/apps/ai_studio/serializers.py`
- Create: `backend/apps/ai_studio/views.py`
- Create: `backend/apps/ai_studio/urls.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/config/settings/base.py`
- Modify: `backend/.env.example`
- Create migration: `backend/apps/ai_studio/migrations/`
- Create: `backend/apps/ai_studio/tests/test_api.py`

**Interfaces:**
- Consumes: `AIGeneration`, `GenerationRequest`, existing `remaining_quota(user)`.
- Produces: `AIDailyBudget(day: date, spent_usd: Decimal, reserved_usd: Decimal)`; `reserve_generation(user, *, estimated_cost: Decimal, params: dict) -> AIGeneration`; owner-scoped `POST/GET /api/v1/ai/generations/`, `GET/DELETE /api/v1/ai/generations/{id}/`, and authenticated input/result streaming endpoints.

- [x] **Step 1: Write failing API/service tests** for auth, owner isolation, 10 MiB upload cap, 25-megapixel cap, supported image formats, five-per-user/day limit, USD 5 daily global estimate, budget reservation concurrency, private storage paths, authenticated image streaming, and delete removing both media files.
- [x] **Step 2: Run** `uv run pytest apps/ai_studio/tests/test_api.py -q`; confirm failures.
- [x] **Step 3: Implement** upload validation before storage/provider calls; use one `AIDailyBudget` row per `timezone.localdate()` locked with `select_for_update`, reserve the provider's per-job estimate atomically, and enforce the existing user quota of five jobs per local day. Add `AI_STUDIO_DAILY_BUDGET_USD=5.00` and `AI_STUDIO_RETENTION_DAYS=30` settings. Reject requests when `spent_usd + reserved_usd + estimated_cost` exceeds the cap; expose only safe failure messages.
- [x] **Step 4: Implement** a private storage backend in `apps/ai_studio/storage.py`: local files live outside `MEDIA_ROOT`; deployments use a private bucket (not the public product-media bucket). Never serialize direct object URLs. Stream files only after checking owner/staff access, and delete storage objects before deleting rows. Generate and apply migrations.
- [x] **Step 5: Run focused tests** and `uv run python manage.py makemigrations --check --dry-run`.

### Task 2: Real providers, Celery generation, and 30-day cleanup

**Files:**
- Modify: `backend/apps/ai_studio/providers/replicate.py`
- Modify: `backend/apps/ai_studio/providers/fal.py`
- Create: `backend/apps/ai_studio/providers/__init__.py` if absent or add provider registry there
- Create: `backend/apps/ai_studio/tasks.py`
- Modify: `backend/apps/ai_studio/services.py`
- Modify: `backend/config/celery.py`
- Modify: `backend/config/settings/base.py`
- Modify: `backend/.env.example`
- Test: `backend/apps/ai_studio/tests/test_providers.py`
- Test: `backend/apps/ai_studio/tests/test_tasks.py`

**Interfaces:**
- Consumes: `ImageProvider.generate(request: GenerationRequest) -> GenerationResult`; Task 1 budget reservation.
- Produces: `ImageProvider.estimate_cost(request: GenerationRequest) -> Decimal`; `get_image_provider() -> ImageProvider`; `generate_image_task(generation_id: str) -> None`; `cleanup_expired_generations() -> int`.

- [x] **Step 1: Write HTTP-mocked adapter tests** for Replicate and fal request/auth/response mapping, timeout, provider rejection, invalid output URL/bytes, and reported cost.
- [x] **Step 2: Run** `uv run pytest apps/ai_studio/tests/test_providers.py -q`; confirm failures.
- [x] **Step 3: Verify official API behavior** for supported image-to-image models, auth, polling/synchronous response, pricing, and file-upload mechanism. Update `GenerationRequest` to carry bounded `image_bytes: bytes | None`; adapters upload input bytes through each provider's documented upload endpoint and download result bytes before persisting them privately. Implement explicit timeouts/error handling and no credential leakage.
- [x] **Step 4: Write failing task tests** for queued→running→done, queued→running→failed, actual-cost recording/reservation release, retry safety, and storage writes; then implement and test the Celery task. On successful provider response, transfer the reserved estimate to `spent_usd` and record reported cost; on a failure with unknown provider charge, conservatively retain the estimate in `spent_usd`.
- [x] **Step 5: Add daily cleanup** for generations created more than 30 days ago, deleting storage objects before records; register a Celery Beat schedule and test the boundary date. Owner deletion of queued/running jobs marks them failed/cancelled before removing media; tasks must re-check state before persisting a result.
- [x] **Step 6: Run** `uv run pytest apps/ai_studio/tests -q`.

### Task 3: AI studio frontend

**Files:**
- Create: `frontend/src/features/ai-studio/api.ts`
- Create: `frontend/src/features/ai-studio/hooks.ts`
- Create: `frontend/src/features/ai-studio/AIStudioPage.tsx`
- Modify: `frontend/src/features/ai-studio/index.ts`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/i18n/locales/ro/common.json`
- Modify: `frontend/src/i18n/locales/en/common.json`
- Create: `frontend/tests/unit/AIStudioPage.test.tsx`

**Interfaces:**
- Consumes: Task 1 API payloads and Task 2 generation lifecycle; existing `RequireAuth`, `apiClient`, and TanStack Query patterns.
- Produces: lazy authenticated `/ai-studio` page with upload, product/variant selection, scene/style selection, polling, quota/spend messaging, retry, and delete.

- [x] **Step 1: Write failing component/API tests** for upload submission, progress polling, completed result, failed-job recovery, limit response, and delete.
- [x] **Step 2: Run** `pnpm exec vitest run tests/unit/AIStudioPage.test.tsx` from `frontend/`; confirm failures.
- [x] **Step 3: Implement** typed API functions and a lazy page, following the existing auth and feature patterns. Fetch private input/result images through authenticated API endpoints as blobs; display safe provider errors and explicitly label results as illustrative.
- [x] **Step 4: Run** the focused test, `pnpm typecheck`, `pnpm lint`, `pnpm test`, and `pnpm build`.

### Task 4: Setup and cost/privacy documentation

**Files:**
- Modify: `docs/SETUP.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `docs/ROADMAP.md`

- [x] **Step 1: Document** provider credentials/mode, model selection, budget/quota variables, Celery worker, local/S3 storage, upload boundaries, 30-day deletion, and user deletion.
- [x] **Step 2: Verify** no real credentials appear in examples and run the complete backend/frontend test suites.
- [ ] **Step 3: Run** one real provider sandbox generation when credentials are configured locally; otherwise report external validation as pending. _(Pending: needs a Replicate or fal key; all provider HTTP is mocked in tests.)_

> The workspace currently has no Git repository; commit each independently tested task after Git is initialized.
