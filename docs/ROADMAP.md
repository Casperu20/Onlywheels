# OnlyWheels – Roadmap & handover

What to do next, in order. Background: [ARCHITECTURE.md §13](architecture/ARCHITECTURE.md#13-implementation-status-as-built)
(what is built and which decisions changed), [SETUP.md](SETUP.md) (installation), [DEPLOYMENT.md](DEPLOYMENT.md).

> **Status:** phases A–G of the implementation plan are written. The code has **not been run yet**:
> it was prepared on a machine without Python packages, Node.js or PostgreSQL. Only Python syntax and the
> translation files were checked. Expect small fixes during the first run (step 1).

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

## 3. Known limitations (technical debt)

| Area | Limitation | Fix |
|---|---|---|
| Data | Fitment specs and products are **demo data** (approximate) | Wheel-Size API or supplier import (CSV via admin) |
| API client | Hand-written `api.ts` per feature | After step 10, switch features to `src/api/generated` gradually |
| Images | Products use a drawn wheel placeholder | Upload photos in admin (`ProductMedia`), S3/R2 in production |
| Search | `icontains` on name/brand + exact SKU | PostgreSQL full-text/trigram, then Meilisearch |
| Background jobs | Celery runs inline (eager) | Redis + worker + beat when Docker is used |
| Emails | Printed to the console | SMTP / Resend in production |
| Payments | Simulated or Stripe test; no refunds via API | Refund from the Stripe dashboard; automate later |
| Invoices / AWB | Not generated (phase 2 structure only) | SmartBill + courier integration |
| Translations | Backend messages are English unless Django has a Romanian translation | Add `locale/ro` with `makemessages` |
| PWA / offline | Not configured | `vite-plugin-pwa` |
| Tests | No end-to-end tests; nothing has run yet | Step 1, then Playwright happy path |
| Infra | No Docker for the app, no CI | Dockerfile + GitHub Actions ([DEPLOYMENT.md §5](DEPLOYMENT.md)) |
| Garage partners | Use Django Admin (restricted) | React portal if needed |
| Legal | No terms/privacy/cookie pages | Required before real customers |

## 4. Next steps (priority order)

### 4.1 Stabilize (after the first run)
1. Fix first-run issues, commit lock files, migrations and the generated API client.
2. Agree the Git workflow: `main` protected, feature branches, pull request reviewed by the other developer.
3. GitHub Actions: `pytest` + `ruff` (backend), `typecheck` + `lint` + `test` (frontend) on every pull request.
4. Replace demo data where possible; add real product photos.

### 4.2 Deploy the demo on the domain
Follow [DEPLOYMENT.md](DEPLOYMENT.md): Cloudflare DNS, frontend on Cloudflare Pages, API on a VPS or Render,
managed PostgreSQL, Stripe test webhook.

### 4.3 Phase 2 features (structure already in the code)

| Feature | Where the design notes are | Backend work | Frontend work |
|---|---|---|---|
| 3D showroom | `frontend/src/features/showroom3d/index.ts` | `Model3D` model + GLB upload in admin | three.js / react-three-fiber configurator page |
| AI photo studio | `backend/apps/ai_studio/services.py`, `providers/` | API endpoints, Celery task, provider adapter | Upload + polling + gallery (`features/ai-studio`) |
| Invoicing (SmartBill + e-Factura) | `backend/apps/invoicing/services.py` | Task after payment, PDF storage | Invoice link on the order page |
| Courier AWB | `backend/apps/shipping/services.py`, `providers/` | AWB on "processing", tracking task | Tracking link/status on the order page |
| Netopia + installments | `backend/apps/payments/providers/netopia.py` | Provider + webhook | Installment option at checkout |
| PWA | — | — | `vite-plugin-pwa`, icons, offline catalog cache |

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
| 4.1 | First run backend, migrations, seed, pytest, CI backend job | First run frontend, generate API client, typecheck/lint/test, CI frontend job |
| 4.1 | Real data import (CSV), product photos in admin | Switch features to the generated client, fix UI issues from the walkthrough |
| 4.2 | Server, PostgreSQL, env, Stripe webhook, email provider | Cloudflare Pages, `VITE_API_URL`, SPA redirects |
| 4.3 | Invoicing + shipping integrations, AI studio API | 3D showroom, AI studio UI, PWA |
| 4.4 | FCM push, token endpoints | Capacitor project, native adapters, Play Store build |

## 6. Open decisions

- Git workflow (proposed above) – not decided yet.
- Hosting for the API: VPS (cheaper, more setup) vs Render/Railway (simpler).
- Fitment data source after the demo (paid API vs manual/supplier data).
