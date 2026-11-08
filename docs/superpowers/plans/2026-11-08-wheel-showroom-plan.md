# Wheel-First 3D Showroom Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the showroom placeholder with a lazy-loaded 3D wheel viewer that uses licensed product GLBs uploaded in Django Admin and works gracefully when assets or WebGL are unavailable.

**Architecture:** Reuse the catalog API's `model_3d` URL and finish materials. Let users choose a wheel product/variant and render the product GLB in a separately loaded React Three Fiber scene; do not ship or depend on car models.

**Tech Stack:** React 19, TypeScript, React Router 7, Vite, React Three Fiber, Three.js, Drei, Vitest, Testing Library.

**Spec:** [2026-11-08-phase-2-sandbox-design.md](../specs/2026-11-08-phase-2-sandbox-design.md)

## Global Constraints

- Use no unlicensed third-party model assets.
- The first showroom is wheel-first; car models can be added later without changing the product-model contract.
- Keep rendering dependencies out of the initial route bundle.
- Handle loading, asset errors, missing GLB, mobile constraints, and unsupported WebGL without breaking product browsing.

## Review Focus

- A missing product GLB must show an actionable empty state — test missing `model_3d`.
- GLB network/parse failures must provide recovery without crashing the route — test loader error.
- Unsupported WebGL must fall back to product media and text — test capability fallback.
- Finish data may be absent or partial — test safe material defaults.
- Large 3D libraries must not enter the initial JS chunk — verify generated chunk graph/build output.

---

### Task 1: 3D viewer dependency and lazy scene

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/pnpm-lock.yaml`
- Create: `frontend/src/features/showroom3d/WheelViewer.tsx`
- Create: `frontend/src/features/showroom3d/ModelCanvas.tsx`
- Modify: `frontend/src/features/showroom3d/index.ts`
- Create: `frontend/tests/unit/WheelViewer.test.tsx`

**Interfaces:**
- Consumes: `ProductDetail["model_3d"]` and `Variant` from `features/catalog/api.ts`.
- Produces: `WheelViewer({ model, finish }: { model: ProductDetail["model_3d"]; finish: string })`; an isolated lazy scene for a GLB model.

- [x] **Step 1: Add only the required runtime dependencies** (`three`, `@react-three/fiber`, `@react-three/drei`) and run `pnpm install`.
- [x] **Step 2: Write failing tests** for missing model state, loading state, failed GLB load, supported model rendering, partial finish-material config, and no-WebGL fallback.
- [x] **Step 3: Run** `pnpm exec vitest run tests/unit/WheelViewer.test.tsx` from `frontend/`; confirm failures.
- [x] **Step 4: Implement** an accessible loading/error/fallback UI and an isolated canvas with camera controls, sensible wheel framing, and safe finish defaults. Mock canvas/GLTF hooks in jsdom tests.
- [x] **Step 5: Run** focused tests, `pnpm typecheck`, and `pnpm lint`.

### Task 2: Showroom page and route

**Files:**
- Create: `frontend/src/features/showroom3d/ShowroomPage.tsx`
- Modify: `frontend/src/features/showroom3d/index.ts`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/features/catalog/api.ts`
- Modify: `frontend/src/i18n/locales/ro/common.json`
- Modify: `frontend/src/i18n/locales/en/common.json`
- Create: `frontend/tests/unit/ShowroomPage.test.tsx`

**Interfaces:**
- Consumes: Task 1 `WheelViewer`; existing `catalogApi.products()` and `catalogApi.product(slug)`.
- Produces: lazy `/showroom` page that selects an active wheel product/variant, loads the model and finish options, and accepts an optional product slug from the query string.

- [x] **Step 1: Write failing page tests** for product selection, query-string selection, variant/finish change, missing model guidance, product loading errors, and mobile-friendly fallback.
- [x] **Step 2: Run** `pnpm exec vitest run tests/unit/ShowroomPage.test.tsx` from `frontend/`; confirm failures.
- [x] **Step 3: Implement** typed selection state, product detail query, accessible selectors and translated copy; replace only the showroom placeholder route with the lazy page. Keep AI studio on its existing placeholder until its separate plan is executed.
- [x] **Step 4: Run** focused tests, `pnpm typecheck`, `pnpm lint`, `pnpm test`, and `pnpm build`; verify the initial chunk does not include Three.js/R3F/Drei and the showroom chunk does.

### Task 3: Asset workflow and documentation

**Files:**
- Modify: `backend/apps/catalog/models.py` only if GLB validation needs tightening
- Modify: `backend/apps/catalog/admin.py` only if the existing upload workflow needs clearer instructions
- Modify: `docs/SETUP.md`
- Modify: `docs/ROADMAP.md`

- [x] **Step 1: Document** the GLB coordinate/centering/compression requirements already stated by `Model3D`, license/credit requirements, upload workflow, and the deliberate lack of car models.
- [x] **Step 2: Verify** the page works with an admin-uploaded licensed GLB and with no model; do not add sample assets unless their license is verified. _(Done 2026-11-08 in a production build with the real CSP, using a self-made Draco test GLB uploaded via `Model3D`, not committed: render, finish recolour, no-model photo fallback, load-error retry; a licensed GLB is still pending.)_
- [x] **Step 3: Run** the full frontend tests and production build.

> The workspace currently has no Git repository; commit each independently tested task after Git is initialized.
