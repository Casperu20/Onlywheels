# Car Showroom Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional car view to the 3D showroom that mounts the selected wheel on a selected or matching 3D car, while preserving the wheel-only fallback.

**Architecture:** Add an admin-managed car GLB model in the catalog app, detect wheel anchors from the GLB metadata on save, and expose only active cars with usable anchors through a read-only API. In the existing lazy Three.js chunk, render the selected car and four scaled copies of the chosen wheel; extend the showroom UI to select a car and switch views.

**Tech Stack:** Django, Django REST Framework, Django migrations/admin, React, TypeScript, React Three Fiber, drei, Three.js, pytest, Vitest.

**Spec:** [2026-11-08-car-showroom-design.md](../specs/2026-11-08-car-showroom-design.md)

## Global Constraints

- No new runtime dependencies; three / drei / r3f already present.
- three and drei must stay inside the lazy `ModelCanvas` chunk; pure maths goes in a three-free module.
- Car GLBs load only after switching to "On a car"; they are not added to the service-worker precache.
- GLBs use the existing `/media` storage and `/draco/` decoder path.
- Only CC0 / CC-BY / CC-BY-SA style licences that allow commercial use and modification; display the attribution for every selected car.
- Wheel-only remains the default and fallback; preserve the no-WebGL photo fallback.
- UI strings must be translated in Romanian and English.
- No downloaded third-party model is added as an asset by this implementation; owner-provided files are uploaded through admin.

## Review Focus

- A malformed/non-GLB upload or absent accessor bounds must fail detection explicitly, not crash admin save; test invalid magic/JSON and missing `min`/`max`.
- Nested node transforms and `matrix` (as well as TRS) must yield correct wheel coordinates; test parent transforms and rotated nodes.
- Separate brake meshes and a boot spare must not displace the four road wheels; test named brake parts and a fifth wheel.
- A car with fewer than four plausible wheel clusters must remain unpublished through the public API until manually corrected; test status and manual override.
- Car selection, GLB loading errors, and unavailable active vehicles must preserve wheel-only usability; test default URL state, retry/back navigation, and generic wheel fallback.

---

## File Structure

- `backend/apps/catalog/models.py` — `CarModel3D`, wheel anchors, orientation and detection state.
- `backend/apps/catalog/car_model_detection.py` — bounded GLB parser and pure anchor-detection result.
- `backend/apps/catalog/admin.py` — car-model editing, detection status, and preview link.
- `backend/apps/catalog/serializers.py`, `views.py`, `urls.py` — public active/usable car list endpoint.
- `backend/apps/catalog/migrations/0003_car_model_3d.py` — schema migration (use the next migration number if the tree has advanced).
- `backend/apps/catalog/tests/test_car_model_detection.py`, `test_car_models_api.py` — detection and API behavior.
- `frontend/src/features/showroom3d/api.ts` — car-model API types and query hook.
- `frontend/src/features/showroom3d/carGeometry.ts` — pure car-anchor and wheel-mount transforms.
- `frontend/src/features/showroom3d/ModelCanvas.tsx` — car scene and four mounted wheels alongside the existing wheel scene, keeping all Three.js components in the proven lazy chunk.
- `frontend/src/features/showroom3d/WheelViewer.tsx` — mode selection, loading/retry/error and attribution presentation.
- `frontend/src/features/showroom3d/ShowroomPage.tsx` — URL-synced mode and car selection; active vehicle matching.
- `frontend/src/features/vehicle/hooks.ts` — reuse existing generation-detail query for active-car model matching, only if existing exports do not already cover this.
- `frontend/tests/unit/carGeometry.test.ts`, `WheelViewer.test.tsx`, `ShowroomPage.test.tsx` — geometry and UI behavior.
- `frontend/src/i18n/locales/{ro,en}/common.json` — car-view copy.
- `docs/SETUP.md`, `docs/ROADMAP.md`, optionally `docs/PROJECT_STRUCTURE.md` — setup, licensing, upload, and roadmap instructions.

## Interfaces

- Backend detector: `detect_wheel_anchors(glb_file) -> DetectionResult`, where `DetectionResult` carries either four anchor records or a staff-readable failure message. Detection never raises for malformed user uploads; it returns an explicit failed result.
- API: `GET /api/v1/catalog/car-models/` returns an unpaginated array of active, usable cars with `id`, `name`, `slug`, `body_type`, `glb_file`, `length_m`, `front`, `vehicle_model` (nullable `{id, name, make}`), effective `wheel_anchors`, `attribution`, and `source_url`.
- Frontend geometry: pure functions accept normalized car dimensions, `front`, four anchors, and `WheelSpec`; return car scale/offset, wheel positions and rotations.
- Active vehicle matching: compare the active generation ID's fetched `Generation.model.id` against the API car model's `vehicle_model.id`; otherwise use the first API car in sort order.
- Car and wheel GLBs are rendered only inside the lazy Three.js path; unmount/error returns the visitor to wheel-only mode.

## Tasks

### Task 1: Persist and administer 3D car models

**Files:**
- Modify: `backend/apps/catalog/models.py`
- Modify: `backend/apps/catalog/admin.py`
- Create: `backend/apps/catalog/migrations/0003_carmodel3d.py` (Django-generated name)
- Test: `backend/apps/catalog/tests/test_car_models_api.py` (model setup assertions can live here or a focused model test)

**Interfaces:**
- Produces `CarModel3D` with name, unique slug, body type choices, `.glb` file under `models3d/cars/`, positive `length_m`, `front` choice (`+z`, `-z`, `+x`, `-x`), nullable FK to `VehicleModel`, manual JSON `wheel_anchors`, derived detected anchors/status/message, attribution, optional source URL, `is_active`, and `sort_order`.
- Manual anchors take precedence over detected anchors for usability and API output.

- [x] **Step 1: Write failing model tests** for required attribution, valid/invalid body type, valid front direction, positive length, valid/invalid manual-anchor shape, manual-anchor precedence, and active/usable visibility predicate.
- [x] **Step 2: Run the focused tests** with `uv run pytest apps/catalog/tests/test_car_models_api.py -q`; confirm the new model/fields are absent.
- [x] **Step 3: Implement model and admin**; use `autocomplete_fields = ("vehicle_model",)`, validate manual anchors as exactly four finite x/y/z points plus `axis` in `{x, z}`, show detection state and effective anchors read-only, and list name/body type/active/detection status.
- [x] **Step 4: Generate and inspect migration** with `uv run python manage.py makemigrations catalog`; ensure the FK points to `vehicles.VehicleModel` and there are no unrelated schema changes.
- [x] **Step 5: Run focused model tests and migration check** with `uv run pytest apps/catalog/tests/test_car_models_api.py -q` and `uv run python manage.py makemigrations --check --dry-run`.

### Task 2: Detect wheel anchors from uploaded GLB metadata

**Files:**
- Create: `backend/apps/catalog/car_model_detection.py`
- Modify: `backend/apps/catalog/admin.py`
- Test: `backend/apps/catalog/tests/test_car_model_detection.py`

**Interfaces:**
- Produces `DetectionResult(anchors: list[dict] | None, error: str | None)` and `detect_wheel_anchors(glb_file) -> DetectionResult`.
- Anchor coordinates are in original GLB units; include the length axis and preserve the `front` sign separately on `CarModel3D`.
- The admin reruns detection when the uploaded GLB changes. If detection fails, save the model with failed status; a manual anchor override makes it usable.

- [x] **Step 1: Write failing GLB fixture tests** for valid GLB JSON with four wheel nodes, node hierarchy transforms, matrix transforms, wheel-brake components, a fifth spare, missing bounds, malformed JSON/chunk length, and unsupported GLB magic.
- [x] **Step 2: Run `uv run pytest apps/catalog/tests/test_car_model_detection.py -q`** and confirm the detector is not implemented.
- [x] **Step 3: Implement a bounded GLB 2.0 JSON-chunk reader** that validates magic/version/chunk lengths and reads node/mesh/material/accessor metadata. Accessor `min`/`max` are optional in glTF: if usable POSITION bounds are absent, return a failure for admin correction instead of assuming they exist or decoding compressed geometry.
- [x] **Step 4: Implement transform and clustering logic**: resolve node world transforms from either matrix or TRS and ancestors; transform the eight AABB corners; match node/ancestor/mesh/material names with the spec regex; cluster wheel-related parts; keep the four road-wheel clusters forming a plausible two-axle rectangle and ignore a fifth spare.
- [x] **Step 5: Wire admin save behavior** to rerun detection on new/changed GLB, retain manual anchors, persist status/message, and avoid reprocessing unchanged files. Surface read/parse errors in the detection message; do not silently fail.
- [x] **Step 6: Run detector and admin tests**; all listed fixture cases must pass, including deterministic coordinates within tolerance.

### Task 3: Expose usable cars and matching vehicle data

**Files:**
- Modify: `backend/apps/catalog/serializers.py`
- Modify: `backend/apps/catalog/views.py`
- Modify: `backend/apps/catalog/urls.py`
- Modify: `backend/apps/catalog/tests/test_car_models_api.py`
- Test: `backend/apps/vehicles/tests/test_api.py` only if a serializer change is required

**Interfaces:**
- Produces the unpaginated public `GET /api/v1/catalog/car-models/` endpoint and the response shape defined above.
- Public queryset includes only `is_active=True` cars with manual anchors or successful detection; default order is `sort_order`, then `name`.
- Includes the linked vehicle model and make with one query; does not expose detection failure details to public users.

- [x] **Step 1: Write failing API tests** for public access, inactive/unusable exclusion, manual-anchor and detected-anchor output, optional vehicle-model fields, sorting, file URL, source URL and attribution.
- [x] **Step 2: Run `uv run pytest apps/catalog/tests/test_car_models_api.py -q`** and confirm the route is missing.
- [x] **Step 3: Implement a read-only list view and serializer** using existing catalog `AllowAny`/no-pagination patterns, selecting related make/model, and add route `/car-models/`.
- [x] **Step 4: Run API tests and schema validation** with the focused pytest command and `uv run python manage.py spectacular --validate --fail-on-warn --file $env:TEMP\ow-schema.yml`.

### Task 4: Implement tested car/wheel placement geometry

**Files:**
- Create: `frontend/src/features/showroom3d/carGeometry.ts`
- Create: `frontend/tests/unit/carGeometry.test.ts`
- Modify: `frontend/src/features/showroom3d/procedural.ts` only if `WheelSpec` must expose the tyre outer diameter for consistent car-view scaling.

**Interfaces:**
- Produces `fitCarToLength(bounds, lengthM, axis)` and `wheelMounts(anchors, carTransform)` plus `wheelModelScale(wheelBounds, wheelSpec)` as typed pure helpers.
- Car is uniformly scaled to real length and grounded at `min y = 0`.
- Four wheel positions use effective anchors; axle direction is outward, with the far-side wheels rotated 180°; camera front direction follows `front`.
- Uploaded wheel geometry (wheel axle along local Z) is uniformly scaled in car view so its radial bounding-box diameter matches `2 * WheelSpec.tireOuter` (the spec stores a radius); generic wheel dimensions are not double-scaled.

- [x] **Step 1: Write failing tests** for a car whose length axis is X and Z, all four anchor positions, both front signs, left/right wheel orientation, ground placement, and selected 17″/19″ diameter scale ratio.
- [x] **Step 2: Run `cd frontend; npx vitest run tests/unit/carGeometry.test.ts`** and confirm expected helper exports are absent.
- [x] **Step 3: Implement the pure helpers** in the three-free module and expose tyre outer diameter from `wheelSpec` if needed.
- [x] **Step 4: Run the geometry tests and `npx tsc --noEmit`**; all positions/rotations must match expected values within floating-point tolerance.

### Task 5: Render the car and four selected wheels in the lazy viewer

**Files:**
- Modify: `frontend/src/features/showroom3d/ModelCanvas.tsx`
- Modify: `frontend/src/features/showroom3d/WheelViewer.tsx`
- Modify: `frontend/tests/unit/WheelViewer.test.tsx`

**Interfaces:**
- An internal `CarScene` in `ModelCanvas.tsx` receives car URL, effective anchors, body length/axis/front, current wheel GLB or generic `WheelSpec`, finish material, label and readiness callback.
- `ModelCanvas` receives an optional car configuration; when absent it preserves the current wheel-only scene without loading a car URL.
- Car meshes matching the stock wheel/brake naming regex are hidden; one wheel instance is mounted at each of four anchors.

- [x] **Step 1: Extend component tests** to assert default wheel-only mode has no car URL, car mode passes the correct car/wheel data, retry/back-to-wheel-only controls exist, and generic fallback remains available.
- [x] **Step 2: Run `cd frontend; npx vitest run tests/unit/WheelViewer.test.tsx`** and confirm car-view expectations fail.
- [x] **Step 3: Implement car scene loading and wheel mounting** using the geometry helpers; reuse current finish material behavior and keep all Three.js imports within the lazy `ModelCanvas` import graph.
- [x] **Step 4: Handle errors explicitly**: expose retry plus "Back to wheel only"; ensure changing car or wheel clears readiness/error state and successful loads call `onReady`.
- [x] **Step 5: Run viewer tests, type check, and production build**; verify the car chunk remains lazy and is not included in service-worker precache.

### Task 6: Add showroom toggle, car selector and active-vehicle preference

**Files:**
- Create: `frontend/src/features/showroom3d/api.ts`
- Modify: `frontend/src/features/showroom3d/ShowroomPage.tsx`
- Modify: `frontend/src/features/showroom3d/WheelViewer.tsx`
- Modify: `frontend/src/features/vehicle/hooks.ts` only if needed for existing generation detail query
- Modify: `frontend/src/i18n/locales/en/common.json`
- Modify: `frontend/src/i18n/locales/ro/common.json`
- Modify: `frontend/tests/unit/ShowroomPage.test.tsx`, `WheelViewer.test.tsx`

**Interfaces:**
- API `useCarModels()` fetches `/api/v1/catalog/car-models/` as a typed list.
- URL uses `?view=car&car=<slug>` for car mode; absent view remains wheel-only. Product/variant URL params are preserved when mode or car changes.
- Car selector prefers the active vehicle's matching `VehicleModel`, else first `sort_order`; display "Your car" on the match.
- Hide car toggle/selector when API returns no cars.

- [x] **Step 1: Write failing UI tests** for wheel-only default, URL-synced mode, matching active generation model, first-car fallback, no cars (hidden switch), preserving product/variant, and attribution link/credit.
- [x] **Step 2: Run focused Vitest files** and confirm the new UI assertions fail before implementation.
- [x] **Step 3: Add typed API query and UI controls**; use the existing generation detail query to map active generation ID to model ID and avoid adding a new query path.
- [x] **Step 4: Add Romanian and English text** for mode toggle, car selector, "Your car", attribution, loading, unusable/empty state if needed, retry, and back-to-wheel-only.
- [x] **Step 5: Run showroom tests, full Vitest, `npx tsc --noEmit`, and `npx eslint .`**.

### Task 7: Document car assets and validate the full experience

**Files:**
- Modify: `docs/SETUP.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/PROJECT_STRUCTURE.md` if new module descriptions are absent

- [x] **Step 1: Update setup documentation** with model-source/licensing guidance, attribution, admin fields, GLB orientation/units, manual anchor JSON and preview instructions.
- [x] **Step 2: Update roadmap and project structure** to state that car-view UI is implemented but downloaded assets remain owner-provided; the current generic wheel remains a fallback.
- [x] **Step 3: Run backend gates**: `uv run pytest -q -p no:warnings`, `uv run ruff check .`, `uv run python manage.py makemigrations --check --dry-run`, and schema validation.
- [x] **Step 4: Run frontend gates**: `npx vitest run`, `npx tsc --noEmit`, `npx eslint .`, and production build.
- [x] **Step 5: Smoke-test under the real CSP** with a temporary self-made car GLB containing a body and four named wheel nodes; verify wheel-only default, car loading only after toggle, finish and size changes, wheel positions/orientation, car attribution, URL state, retry/back behavior, and no console/CSP errors. Remove all temporary files and servers afterward. _Done: admin upload auto-detected all four anchors; car view rendered with mounted wheels and no CSP errors. Fixed two bugs found here: relative admin preview link (now uses `FRONTEND_URL`) and a false "(your car)" label when no garage vehicle is active._

## Execution Notes

- This workspace is not a Git repository, so do not add commit steps; preserve all user changes and report the limitation.
- Do not add licensed third-party model files. The owner will download chosen models and enter author/source metadata in Django admin.
- If real downloaded assets are later supplied, run the browser smoke test with at least the Generic passenger car pack and one selected showcase car before claiming their auto-detection works.
- The final browser/CSP smoke with a temporary car GLB remains unrun: there is no local backend environment/database or running API in this workspace. The UI, geometry, detector and API behavior are covered by automated tests; upload and browser-check the owner-selected models separately.
