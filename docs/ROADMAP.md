# OnlyWheels – Roadmap & handover

What to do next, in order. Background: [ARCHITECTURE.md §13](architecture/ARCHITECTURE.md#13-implementation-status-as-built)
(what is built and which decisions changed), [SETUP.md](SETUP.md) (installation), [ANDROID.md](ANDROID.md) (Capacitor debug app), [DEPLOYMENT.md](DEPLOYMENT.md).

> **Status:** phases A–I (MVP, Phase-2 integrations, production readiness, and the Capacitor Android shell) are
> implemented, committed with lock files/migrations/generated OpenAPI types, and verified locally on PostgreSQL 16:
> - **backend:** `manage.py check`, linear migrations across all apps, **366 pytest tests passing**, `ruff` clean,
>   strict OpenAPI schema validation (`spectacular --validate --fail-on-warn`), `seed_demo` idempotent, declarative
>   fitment engine, Wheel-Size read-through + stale-while-revalidate sync with atomic bulk make reconciliation,
>   scoped order reservation expiry, late-payment slot/stock guards, and dual auth (web httpOnly cookies + CSRF and
>   native `/api/v1/auth/native/*` Bearer JWTs);
> - **frontend:** `tsc --noEmit` clean, ESLint clean, **19 Vitest suites (128 tests) passing**, Orval OpenAPI client
>   committed in `src/api/generated/` and wired to domain models, integer minor-unit (`bani`) currency math,
>   single-flight CSRF deduplication, 3D wheel + car showroom (`/showroom`), AI Photo Studio (`/ai-studio`), invoice
>   downloads + AWB tracking on order pages, and production Vite + Workbox PWA build;
> - **Android (Capacitor 8):** `frontend/android` (`ro.onlywheels.app`), Keystore-backed native token cache with
>   self-healing corruption recovery (`@aparajita/capacitor-secure-storage`), in-app fake-payment routing +
>   `onlywheels://checkout/success` deep-link return, web Google Sign-In hidden on native, Service Worker disabled
>   for Capacitor builds (`CAPACITOR_BUILD=1`), and cross-platform `scripts/android-build.mjs`.
>
> **Still requiring external accounts or hardware:** running the Android debug APK on a physical phone/emulator over
> an HTTPS tunnel ([ANDROID.md](ANDROID.md)), live sandbox/merchant credentials for Stripe/NETOPIA/SmartBill/Sameday/FAN
> Courier/Replicate/fal, and optional hosted production deployment.

---

## 1. Running on a development machine

Lock files (`backend/uv.lock`, `frontend/pnpm-lock.yaml`), Django migrations, and the generated API client
(`frontend/src/api/generated/`) are already committed in Git. For daily startup, see [QUICKSTART.md](../QUICKSTART.md);
for setting up a brand-new laptop, follow [SETUP.md §0.1](SETUP.md#01-second-developer--joining-the-existing-repository):

| # | Step | Command | Expected result |
|---|---|---|---|
| 1 | Install tools + PostgreSQL | [SETUP.md §1–2](SETUP.md) | `uv`, `node`, `pnpm`, Docker PostgreSQL (or native `psql`) work |
| 2 | Backend dependencies | `cd backend; uv sync` | `.venv` created from `uv.lock` |
| 3 | Environment | copy `.env.example` → `.env`, set `DATABASE_URL`, `DJANGO_SECRET_KEY` | — |
| 4 | Migrate & seed | `uv run python manage.py migrate; uv run python manage.py seed_demo` | all migrations applied; 13 car generations, 14 products, 4 garages, 2 vouchers seeded |
| 5 | Backend checks | `uv run pytest` · `uv run ruff check .` | 366 tests pass, ruff clean |
| 6 | API docs | `uv run python manage.py runserver`, open `/api/docs/` | Swagger UI loads without errors |
| 7 | Frontend dependencies | `cd frontend; Copy-Item .env.example .env.local; pnpm install` | `node_modules` installed from `pnpm-lock.yaml` |
| 8 | Frontend checks | `pnpm typecheck` · `pnpm lint` · `pnpm test` · `pnpm build` | 19 test files (128 tests) pass, build succeeds |
| 9 | Run the web app | `pnpm dev`, open http://localhost:5173 | home page with vehicle selector |
| 10 | Android debug app (optional) | follow [ANDROID.md](ANDROID.md) (`pnpm android:sync` · `pnpm android:run`) | app launches on emulator/phone against HTTPS backend |

Most likely first-run issues and where to look:

- **Library versions** (`pyproject.toml`, `package.json` use minimum versions): if a newer major version
  breaks something, pin the version that works and commit the lock file.
- **django-unfold / django-import-export** admin integration (`*/admin.py`): admin pages are the
  part most sensitive to versions.
- **TypeScript strictness** (`tsconfig.json`): unused variables or stricter library types.
- **Tests depending on time** (`apps/appointments/tests`): slot tests assume Europe/Bucharest local time.

## 2. Manual demo walkthrough (acceptance check)

1. Home → pick **BMW / Seria 3 / G20** → "Găsește jantele" → catalog shows only fitting wheels.
2. Open a wheel → variants show "Compatibil" / "cu inele de centrare" / reasons why not.
3. As a guest: heart icon → redirected to login. Add 4 wheels to the cart.
4. Register (or Google login) → cart is still there (merged into the account).
5. Checkout → "Montaj la service partener" → pick garage, date, time → voucher `BINEAIVENIT10`.
6. "Plătește online" → simulated payment page → success → order "Plătită", email printed in the backend console
   (customer + garage).
7. Admin (`/admin/`): order visible, stock decreased, appointment "booked"; mark order processing → ready for fitting
   → completed (status emails).
8. Write a review → approve it in admin → rating appears on the product.
9. Switch language RO/EN; check the layout on a phone-sized window.
10. Account → "Datele tale": download the JSON export; delete a test account (orders stay, anonymised).
11. Production build (`pnpm build; pnpm preview`): the browser offers "Install app"; reload works offline for
    pages already visited.

## 3. Known limitations (technical debt)

### 3.1 Prepared for production, switched on by environment variables

All of these are in the code and do nothing until the variable is set (details: [SETUP.md §9](SETUP.md),
[DEPLOYMENT.md](DEPLOYMENT.md)).

| What | Where | Switch |
|---|---|---|
| Error tracking (Sentry) | `config/settings/base.py`, `frontend/src/lib/sentry.ts` | `SENTRY_DSN`, `VITE_SENTRY_DSN` |
| Structured logs (structlog) | `config/settings/base.py` (`LOGGING`) | `LOG_FORMAT=json` (default when `DEBUG=False`) |
| Content-Security-Policy | django-csp (admin, API docs); `frontend/public/_headers` + `infra/nginx/default.conf` (SPA) | `CSP_ENABLED` (default on when `DEBUG=False`) |
| Static files | WhiteNoise, compressed + hashed in `prod.py` | always on |
| Uploads on Cloudflare R2 / S3 | django-storages | `AWS_STORAGE_BUCKET_NAME` + keys |
| Redis cache | django-redis | `CACHE_URL=rediscache://…` |
| Transactional email (Resend) | django-anymail | `EMAIL_BACKEND=anymail.backends.resend.EmailBackend`, `RESEND_API_KEY` |
| PWA | `vite-plugin-pwa` in `vite.config.ts`, icons in `frontend/public/` | on in web `pnpm build`; disabled in Capacitor Android builds (`CAPACITOR_BUILD=1`) |
| Route code splitting | `frontend/src/app/router.tsx` (`lazy`) + `chunkReload.ts` | always on |
| GDPR export / delete account | `GET /api/v1/auth/me/export/`, `POST /api/v1/auth/me/delete/`, Account page | — |
| 3D model data | `catalog.Model3D` wheel GLBs and `catalog.CarModel3D` car GLBs (admin uploads), public car-model API, `/showroom` wheel/car viewer | Upload licensed assets and credit them (see [SETUP.md](SETUP.md)); no third-party models are bundled |
| Docker (production) | `infra/docker/*.Dockerfile`, `infra/docker-compose.prod.yml`, `infra/nginx/` | `docker compose … up` |
| CI | `.github/workflows/ci.yml` | push to GitHub |
| Android app (Capacitor 8) | `frontend/android/`, `frontend/capacitor.config.json`, `frontend/scripts/android-build.mjs`, `src/lib/native/` | `pnpm android:sync` / `pnpm android:run` (see [ANDROID.md](ANDROID.md)) |

### 3.2 Still open

| Area | Limitation | Fix |
|---|---|---|
| Data | Without `WHEEL_SIZE_API_KEY`: 13 demo cars. With the free Sandbox key: all European cars, but only 300 API requests/day and "testing only" licence | Paid Wheel-Size plan before launch; products are still demo data (supplier CSV import) |
| API client | `src/api/generated/` is generated and domain models (`catalog`, `orders`, `checkout`, `auth`) derive canonical types from it; feature query hooks still wrap `apiClient` directly | Optionally migrate remaining query hooks to Orval-generated hooks where helpful |
| Images | Demo photos from Wikimedia Commons (`backend/apps/catalog/demo_media`, `frontend/src/assets/demo`); they show the product type, not the exact product. Author + licence are in `credits.json` and shown under each photo | Real supplier photos uploaded in admin (`ProductMedia`); keep the credit fields for licensed photos |
| Search | `icontains` on name/brand + exact SKU | PostgreSQL full-text/trigram, then Meilisearch |
| Background jobs | Celery runs inline (eager) in development (`CELERY_TASK_ALWAYS_EAGER=True`); Wheel-Size stale refreshes dispatch background tasks when async | Production compose file runs Redis + worker + beat |
| Payments | Supports `card_online` (`fake`, Stripe, NETOPIA), `cash_on_delivery` (ramburs), and `pay_at_garage`; no automated API refunds | Refund from the Stripe/NETOPIA dashboard; automate later |
| Invoices | SmartBill integration is built but disabled until a merchant account is configured (dev issues a local "DEMO" mock-up PDF instead, clearly marked as not a fiscal document); not yet run against the live API; e-Factura status is not automated | Configure SmartBill (see [SETUP.md](SETUP.md)); approved e-Factura workflow |
| AWB | Sameday and FAN Courier adapters are built and HTTP-mocked tested, but disabled until carrier credentials are configured; not yet run against a carrier sandbox. FAN v2 endpoints and both carriers' status names come from unofficial sources. `SHIPPING_CARRIER=demo` simulates the whole flow without an account (development only) | Configure a carrier (see [SETUP.md](SETUP.md)); run one sandbox AWB and check the status mapping |
| AI photo studio | Replicate and fal adapters are built and HTTP-mocked tested, but disabled until an API key is configured; not yet run against a real model. The Replicate Kontext price and fal Kontext input fields beyond `prompt`/`image_url` come from documentation, not a live call; costs are estimates (providers do not report them) | Configure a provider (see [SETUP.md](SETUP.md)); run one generation and compare the cost with the provider dashboard |
| 3D showroom | Wheel and optional car views are implemented. No licensed wheel or car GLBs are shipped: wheels use the code-drawn generic preview until uploaded; the car selector appears after a usable car is uploaded in admin. Car wheel positions are detected from GLB metadata or can be entered manually. The Three.js scene is lazy-loaded on `/showroom` | Upload and credit licensed, Draco-compressed GLBs (see [SETUP.md](SETUP.md)); on Cloudflare Pages + R2 add the R2 CORS rule from [DEPLOYMENT.md](DEPLOYMENT.md) |
| Translations | Backend messages are English unless Django has a Romanian translation | Add `locale/ro` with `makemessages` |
| Tests | Backend (`pytest`, 366 tests) and frontend (`vitest`, 128 tests) run on PostgreSQL locally and in CI; no browser E2E suite yet | Add Playwright happy-path suite |
| Bundle size | Pages and the Three.js showroom (`ModelCanvas`) are lazy-split; shared core bundle is ~705 KB (~224 KB gzipped) | Acceptable for now; revisit with `manualChunks` if needed |
| Android device run | Capacitor Android project, native JWT auth, Keystore storage, and checkout deep links are built and unit/API-tested; device acceptance requires Android Studio SDK + HTTPS backend URL | Follow the step-by-step device checklist in [ANDROID.md](ANDROID.md) |
| Garage partners | Use Django Admin (restricted) | React portal if needed |
| Legal | Terms, privacy, cookies and contact pages are **draft texts** (`/legal/*`, `/contact`) | Have them reviewed by a lawyer; add the real company details |
| Not prepared | Apple login, maps for garages, Django Channels, PostHog analytics | See [ARCHITECTURE.md §13](architecture/ARCHITECTURE.md#13-implementation-status-as-built) |

## 4. Next steps (priority order)

### 4.1 Verify Android debug app on device/emulator
1. Follow [ANDROID.md](ANDROID.md) to point `VITE_API_URL` at an HTTPS tunnel or staging backend, run `pnpm android:sync` + `pnpm android:run`, and tick off the device acceptance checks.
2. Replace demo catalog/fitment data where desired; upload licensed wheel/car `.glb` assets in Django Admin for `/showroom`.

### 4.2 Deploy the demo on a domain (optional for coursework)
Follow [DEPLOYMENT.md](DEPLOYMENT.md): either the single-server Docker stack (`infra/docker-compose.prod.yml`) or
Cloudflare Pages + API on Render/VPS; managed PostgreSQL, Stripe/NETOPIA webhook, Sentry, Resend, R2.

### 4.3 Phase 2 features (structure already in the code)

| Feature | Where the design notes are | Backend work | Frontend work |
|---|---|---|---|
| 3D showroom | `frontend/src/features/showroom3d/` | Done: wheel `Model3D` and admin-managed `CarModel3D`, automatic/manual wheel anchors, and public active-car API | `/showroom` supports wheel-only and car views, active-vehicle matching, URL-synced car/variant selection, generic wheel fallback, attribution, and wheel-only recovery; licensed GLBs remain optional and must be uploaded by the owner |
| AI photo studio | `backend/apps/ai_studio/services.py`, `providers/` | Upload API with EXIF stripping, per-user quota + global USD budget, Replicate/fal adapters, Celery task, private storage, retention cleanup, GDPR export/erasure implemented; disabled until a provider key is configured | `/ai-studio` page (upload, scene/style, polling history, retry/download/delete) and "Try on your car" link on wheel products implemented |
| Invoicing (SmartBill + e-Factura) | `backend/apps/invoicing/services.py` | Paid-order task, private PDF storage, owner/staff API, and staff retry implemented; issuance remains disabled until a test account is confirmed (`SMARTBILL_DEMO` issues a local mock-up PDF in dev); e-Factura automation is not supported | Order-page invoice status and authenticated PDF download implemented |
| Courier AWB | `backend/apps/shipping/services.py`, `providers/` | AWB on "processing" (courier orders), private labels, hourly tracking, admin retry/review implemented; disabled until a carrier is configured | Tracking block (carrier, AWB, status, link) on the order page implemented |
| Netopia + installments | `backend/apps/payments/providers/netopia.py` | Hosted checkout, authenticated callback, and installment persistence implemented; sandbox E2E requires merchant credentials | Existing checkout redirects to NETOPIA; no separate installment-count selector (provider-managed terms must be verified with the merchant account) |
| PWA | `frontend/vite.config.ts` | — | Done (installable, offline catalog cache); later: push notifications, install prompt UI |

### 4.4 Phase 3 – Android (Capacitor)
Implemented in `frontend/android/` (`ro.onlywheels.app`), `frontend/src/lib/native/`, and `backend/apps/accounts/`:
- Native email/password auth (`/api/v1/auth/native/{login,register,refresh,logout}/`) with Keystore-backed write-through token cache (`@aparajita/capacitor-secure-storage`) and active-user refresh enforcement.
- In-app fake checkout routing + `onlywheels://checkout/success?order=...` deep-link listener (`main.tsx`, `deep-links.ts`), web Google Sign-In hidden on native, and `VitePWA` Service Worker disabled on Capacitor builds (`CAPACITOR_BUILD=1`).
- Remaining optional extensions (outside university demo scope): FCM push notifications (`backend/apps/notifications/push.py`), native Google Sign-In SDK, live gateway app-return deep links, and Play Store release signing ([ANDROID.md §7](ANDROID.md#7-optional-extensions-outside-the-current-university-demo)).

### 4.5 Phase 4 – Scale
Meilisearch (`backend/apps/catalog/search_index.py`), Redis caching of fitment results, Django Channels for live
order/AI status, AR, recommendations, garage partner portal.

## 5. Task split (1 frontend + 1 backend developer)

| Step | Backend developer | Frontend developer |
|---|---|---|
| 4.1 | First run backend, migrations, seed, pytest, CI backend job green | First run frontend, generate API client, typecheck/lint/test, CI frontend job green |
| 4.1 | Real data import (CSV), product photos in admin | Switch features to the generated client, fix UI issues from the walkthrough |
| 4.2 | Server/Docker stack, PostgreSQL, env, Stripe webhook, Resend, Sentry, R2 | Cloudflare Pages or nginx image, `VITE_*` values, check CSP in the browser |
| 4.3 | Invoicing + shipping integrations, AI studio API | 3D showroom, AI studio UI |
| 4.4 | FCM push, token endpoints | Capacitor project, native adapters, Play Store build |

## 6. Open decisions

- Git workflow (proposed above) – not decided yet.
- Hosting for the API: VPS (cheaper, more setup) vs Render/Railway (simpler).
- Fitment data source after the demo (paid API vs manual/supplier data).
