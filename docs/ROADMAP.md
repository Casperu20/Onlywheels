# OnlyWheels – Roadmap & handover

What to do next, in order. Background: [ARCHITECTURE.md §13](architecture/ARCHITECTURE.md#13-implementation-status-as-built)
(what is built and which decisions changed), [SETUP.md](SETUP.md) (installation), [DEPLOYMENT.md](DEPLOYMENT.md).

> **Status:** phases A–G of the implementation plan plus the **production-readiness batch** (§3.1) are written and
> were **tested in a temporary, isolated environment** (Python 3.11 venv + portable Node 22, SQLite instead of
> PostgreSQL):
> - backend: `manage.py check`, migrations for all apps, **147 pytest tests passed**, ruff clean,
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
| 3D model data | `catalog.Model3D` (GLB upload in the product admin), `model_3d` in product detail | upload a `.glb` |
| Docker (production) | `infra/docker/*.Dockerfile`, `infra/docker-compose.prod.yml`, `infra/nginx/` | `docker compose … up` |
| CI | `.github/workflows/ci.yml` | push to GitHub |
| Android shell | `frontend/capacitor.config.json` | `npx cap add android` (phase 3) |

### 3.2 Still open

| Area | Limitation | Fix |
|---|---|---|
| Data | Fitment specs and products are **demo data** (approximate) | Wheel-Size API or supplier import (CSV via admin) |
| API client | Hand-written `api.ts` per feature | After step 10, switch features to `src/api/generated` gradually |
| Images | Products use a drawn wheel placeholder | Upload photos in admin (`ProductMedia`) |
| Search | `icontains` on name/brand + exact SKU | PostgreSQL full-text/trigram, then Meilisearch |
| Background jobs | Celery runs inline (eager) in development | Production compose file runs Redis + worker + beat |
| Payments | Simulated or Stripe test; no refunds via API | Refund from the Stripe dashboard; automate later |
| Invoices / AWB | Not generated (phase 2 structure only) | SmartBill + courier integration |
| Translations | Backend messages are English unless Django has a Romanian translation | Add `locale/ro` with `makemessages` |
| Tests | No end-to-end test suite (flows checked manually); not yet run on PostgreSQL | Playwright happy path; CI runs PostgreSQL |
| Bundle size | Pages are split, but the shared bundle is still ~645 KB (~205 KB gzipped): React DOM, React Router, zod, axios, i18next | Acceptable for now; revisit with `manualChunks` / lighter libraries if needed |
| Docker / CI | Written but never executed here | Run once on a machine with Docker / on GitHub; fix paths if needed |
| Garage partners | Use Django Admin (restricted) | React portal if needed |
| Legal | No terms/privacy/cookie pages (the GDPR endpoints exist) | Required before real customers |
| Not prepared | Apple login, maps for garages, Wheel-Size API, Django Channels, PostHog analytics | See [ARCHITECTURE.md §13](architecture/ARCHITECTURE.md#13-implementation-status-as-built) |

## 4. Next steps (priority order)

### 4.1 Stabilize (after the first run)
1. Fix first-run issues, commit lock files, migrations and the generated API client.
2. Agree the Git workflow: `main` protected, feature branches, pull request reviewed by the other developer.
3. Push to GitHub: `.github/workflows/ci.yml` runs ruff + migrations check + schema check + pytest on PostgreSQL,
   typecheck + lint + test + build for the frontend, and builds both Docker images. Make it green, then make it
   a required check on `main`.
4. Replace demo data where possible; add real product photos.

### 4.2 Deploy the demo on the domain
Follow [DEPLOYMENT.md](DEPLOYMENT.md): either the single-server Docker stack (`infra/docker-compose.prod.yml`) or
Cloudflare Pages + API on Render/VPS; managed PostgreSQL, Stripe test webhook, Sentry, Resend, R2.

### 4.3 Phase 2 features (structure already in the code)

| Feature | Where the design notes are | Backend work | Frontend work |
|---|---|---|---|
| 3D showroom | `frontend/src/features/showroom3d/index.ts` | Done: `Model3D` + GLB upload in admin + `model_3d` in the API | three.js / react-three-fiber configurator page |
| AI photo studio | `backend/apps/ai_studio/services.py`, `providers/` | API endpoints, Celery task, provider adapter | Upload + polling + gallery (`features/ai-studio`) |
| Invoicing (SmartBill + e-Factura) | `backend/apps/invoicing/services.py` | Task after payment, PDF storage | Invoice link on the order page |
| Courier AWB | `backend/apps/shipping/services.py`, `providers/` | AWB on "processing", tracking task | Tracking link/status on the order page |
| Netopia + installments | `backend/apps/payments/providers/netopia.py` | Provider + webhook | Installment option at checkout |
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
