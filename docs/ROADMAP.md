# OnlyWheels – Roadmap & handover

What to do next, in order. Background: [ARCHITECTURE.md §13](architecture/ARCHITECTURE.md#13-implementation-status-as-built)
(what is built and which decisions changed), [SETUP.md](SETUP.md) (installation), [DEPLOYMENT.md](DEPLOYMENT.md).

> **Status:** phases A–G of the implementation plan plus the **production-readiness batch** (§3.1) are written and
> were **tested in a temporary, isolated environment** (Python 3.11 venv + portable Node 22, SQLite instead of
> PostgreSQL):
> - backend: `manage.py check`, migrations for all apps, **153 pytest tests passed**, ruff clean,
>   OpenAPI schema valid (strict), every Django Admin page renders, `seed_demo` runs twice;
>   production settings: `check --deploy` (only the expected test-key / HSTS-preload warnings), `collectstatic`
>   with WhiteNoise, JSON logs;
> - frontend: `tsc` clean, ESLint clean, **34 Vitest tests passed**, production build OK (code-split routes,
>   service worker + manifest generated), orval client generated from the live schema and type-checks;
> - end to end in a real browser: car selection → compatible wheels → guest cart → register (cart merged) →
>   checkout with garage slot + voucher → simulated payment → order paid, appointment booked, emails sent;
>   later: service worker registered and auto-updated, lazy pages load, GDPR export + account deletion,
>   Django Admin and Swagger UI work with the Content-Security-Policy switched on.
>
> Not tested yet: PostgreSQL, Python 3.12, Stripe test mode, Google login (need keys/accounts), the Docker images
> and the GitHub Actions workflow (no Docker/GitHub runner here), Sentry/R2/Resend/Redis with real accounts, the
> offline mode of the PWA. Lock files, migrations and the generated client were not kept – create and commit them
> in step 1 (CI needs them).

---

## 1. First run on the development machine (do this first)

| # | Step | Command | Expected result |
|---|---|---|---|
| 1 | Install tools + PostgreSQL | [SETUP.md §1–2](SETUP.md) | `uv`, `node`, `pnpm`, `psql` work |
| 2 | Backend dependencies | `cd backend; uv sync` | `.venv` created, `uv.lock` written → **commit `uv.lock`** |
| 3 | Environment | copy `.env.example` → `.env`, set `DATABASE_URL`, `DJANGO_SECRET_KEY` | — |
| 4 | Migrations | `uv run python manage.py makemigrations` then `migrate` | migrations created for all apps → **commit them** |
| 5 | Demo data | `uv run python manage.py seed_demo` | 13 car generations, 14 products, 4 garages, 2 vouchers |
| 6 | Backend checks | `uv run pytest` · `uv run ruff check .` | all green |
| 7 | API docs | `runserver`, open `/api/docs/` | Swagger loads without errors |
| 8 | Frontend dependencies | `cd frontend; pnpm install` | `pnpm-lock.yaml` written → **commit it** |
| 9 | Frontend checks | `pnpm typecheck` · `pnpm lint` · `pnpm test` | all green |
| 10 | Generate API client | backend running → `pnpm api:generate` | `src/api/generated/` filled → **commit it** |
| 11 | Run the app | `pnpm dev`, open http://localhost:5173 | home page with vehicle selector |
| 12 | GitHub + CI | commit, create the repository, push ([SETUP.md §10](SETUP.md#10-git-github-and-ci-one-time)) | CI green; teammate added; `main` protected |

The full order of steps 1–12 on a new laptop: [SETUP.md §0](SETUP.md#0-preparing-a-new-laptop--the-whole-sequence).

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
| PWA | `vite-plugin-pwa` in `vite.config.ts`, icons in `frontend/public/` | always on in `pnpm build` |
| Route code splitting | `frontend/src/app/router.tsx` (`lazy`) | always on |
| GDPR export / delete account | `GET /api/v1/auth/me/export/`, `POST /api/v1/auth/me/delete/`, Account page | — |
| 3D model data | `catalog.Model3D` wheel GLBs and `catalog.CarModel3D` car GLBs (admin uploads), public car-model API, `/showroom` wheel/car viewer | Upload licensed assets and credit them (see [SETUP.md](SETUP.md)); no third-party models are bundled |
| Docker (production) | `infra/docker/*.Dockerfile`, `infra/docker-compose.prod.yml`, `infra/nginx/` | `docker compose … up` |
| CI | `.github/workflows/ci.yml` | push to GitHub |
| Android shell | `frontend/capacitor.config.json` | `npx cap add android` (phase 3) |

### 3.2 Still open

| Area | Limitation | Fix |
|---|---|---|
| Data | Without `WHEEL_SIZE_API_KEY`: 13 demo cars. With the free Sandbox key: all European cars, but only 300 API requests/day and "testing only" licence | Paid Wheel-Size plan before launch; products are still demo data (supplier CSV import) |
| API client | Hand-written `api.ts` per feature | After step 10, switch features to `src/api/generated` gradually |
| Images | Demo photos from Wikimedia Commons (`backend/apps/catalog/demo_media`, `frontend/src/assets/demo`); they show the product type, not the exact product. Author + licence are in `credits.json` and shown under each photo | Real supplier photos uploaded in admin (`ProductMedia`); keep the credit fields for licensed photos |
| Search | `icontains` on name/brand + exact SKU | PostgreSQL full-text/trigram, then Meilisearch |
| Background jobs | Celery runs inline (eager) in development | Production compose file runs Redis + worker + beat |
| Payments | Simulated or Stripe test; no refunds via API | Refund from the Stripe dashboard; automate later |
| Invoices | SmartBill integration is built but disabled until a merchant account is configured (dev issues a local "DEMO" mock-up PDF instead, clearly marked as not a fiscal document); not yet run against the live API; e-Factura status is not automated | Configure SmartBill (see [SETUP.md](SETUP.md)); approved e-Factura workflow |
| AWB | Sameday and FAN Courier adapters are built and HTTP-mocked tested, but disabled until carrier credentials are configured; not yet run against a carrier sandbox. FAN v2 endpoints and both carriers' status names come from unofficial sources. `SHIPPING_CARRIER=demo` simulates the whole flow without an account (development only) | Configure a carrier (see [SETUP.md](SETUP.md)); run one sandbox AWB and check the status mapping |
| AI photo studio | Replicate and fal adapters are built and HTTP-mocked tested, but disabled until an API key is configured; not yet run against a real model. The Replicate Kontext price and fal Kontext input fields beyond `prompt`/`image_url` come from documentation, not a live call; costs are estimates (providers do not report them) | Configure a provider (see [SETUP.md](SETUP.md)); run one generation and compare the cost with the provider dashboard |
| 3D showroom | Wheel and optional car views are implemented. No licensed wheel or car GLBs are shipped: wheels use the code-drawn generic preview until uploaded; the car selector appears after a usable car is uploaded in admin. Car wheel positions are detected from GLB metadata or can be entered manually. The Three.js scene is lazy-loaded on `/showroom` | Upload and credit licensed, Draco-compressed GLBs (see [SETUP.md](SETUP.md)); on Cloudflare Pages + R2 add the R2 CORS rule from [DEPLOYMENT.md](DEPLOYMENT.md) |
| Translations | Backend messages are English unless Django has a Romanian translation | Add `locale/ro` with `makemessages` |
| Tests | No end-to-end test suite (flows checked manually); not yet run on PostgreSQL | Playwright happy path; CI runs PostgreSQL |
| Bundle size | Pages are split, but the shared bundle is still ~680 KB (~215 KB gzipped): React DOM, React Router, zod, axios, i18next | Acceptable for now; revisit with `manualChunks` / lighter libraries if needed |
| Docker / CI | Written but never executed here | Run once on a machine with Docker / on GitHub; fix paths if needed |
| Garage partners | Use Django Admin (restricted) | React portal if needed |
| Legal | Terms, privacy, cookies and contact pages are **draft texts** (`/legal/*`, `/contact`) | Have them reviewed by a lawyer; add the real company details |
| Not prepared | Apple login, maps for garages, Django Channels, PostHog analytics | See [ARCHITECTURE.md §13](architecture/ARCHITECTURE.md#13-implementation-status-as-built) |

## 4. Next steps (priority order)

### 4.1 Stabilize (after the first run)
1. Fix first-run issues, commit lock files, migrations and the generated API client.
2. Agree the Git workflow: `main` protected, feature branches, pull request reviewed by the other developer.
3. Push to GitHub: `.github/workflows/ci.yml` runs ruff + migrations check + schema check + pytest on PostgreSQL,
   typecheck + lint + test + build for the frontend, and builds both Docker images. Make it green, then make it
   a required check on `main`.
4. Replace demo data where possible; add real product photos from suppliers.

### 4.2 Deploy the demo on the domain
Follow [DEPLOYMENT.md](DEPLOYMENT.md): either the single-server Docker stack (`infra/docker-compose.prod.yml`) or
Cloudflare Pages + API on Render/VPS; managed PostgreSQL, Stripe test webhook, Sentry, Resend, R2.

### 4.3 Phase 2 features (structure already in the code)

| Feature | Where the design notes are | Backend work | Frontend work |
|---|---|---|---|
| 3D showroom | `frontend/src/features/showroom3d/` | Done: wheel `Model3D` and admin-managed `CarModel3D`, automatic/manual wheel anchors, and public active-car API | `/showroom` supports wheel-only and car views, active-vehicle matching, URL-synced car/variant selection, generic wheel fallback, attribution, and wheel-only recovery; licensed GLBs remain optional and must be uploaded by the owner |
| AI photo studio | `backend/apps/ai_studio/services.py`, `providers/` | Upload API with EXIF stripping, per-user quota + global USD budget, Replicate/fal adapters, Celery task, private storage, retention cleanup, GDPR export/erasure implemented; disabled until a provider key is configured | `/ai-studio` page (upload, scene/style, polling history, retry/download/delete) and "Try on your car" link on wheel products implemented |
| Invoicing (SmartBill + e-Factura) | `backend/apps/invoicing/services.py` | Paid-order task, private PDF storage, owner/staff API, and staff retry implemented; issuance remains disabled until a test account is confirmed (`SMARTBILL_DEMO` issues a local mock-up PDF in dev); e-Factura automation is not supported | Order-page invoice status and authenticated PDF download implemented |
| Courier AWB | `backend/apps/shipping/services.py`, `providers/` | AWB on "processing" (courier orders), private labels, hourly tracking, admin retry/review implemented; disabled until a carrier is configured | Tracking block (carrier, AWB, status, link) on the order page implemented |
| Netopia + installments | `backend/apps/payments/providers/netopia.py` | Hosted checkout, authenticated callback, and installment persistence implemented; sandbox E2E requires merchant credentials | Existing checkout redirects to NETOPIA; no separate installment-count selector (provider-managed terms must be verified with the merchant account) |
| PWA | `frontend/vite.config.ts` | — | Done (installable, offline catalog cache); later: push notifications, install prompt UI |

### 4.4 Phase 3 – Android
`npx cap add android`; native adapters in `frontend/src/lib/native/` switch to Capacitor plugins;
the API already accepts `Authorization: Bearer` tokens for the app; push via FCM
(`backend/apps/notifications/push.py`).

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
