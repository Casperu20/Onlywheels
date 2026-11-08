# Development setup

Everything below runs on the **development machine**. This repository only contains source and config;
nothing has to be installed globally except the tools in step 1.

## 0. Preparing a new laptop – the whole sequence

Do the steps in this order; each links to the details. The order matters: lock files and migrations must exist
before the first push, otherwise the first CI run fails.

| # | What | Details | Result |
|---|---|---|---|
| 1 | Install the tools, create a GitHub account | [§1](#1-tools-one-time) | `git`, `uv`, `node`, `pnpm` work |
| 2 | Get the code: extract `onlywheels.zip` (e.g. to `C:\dev\`) or `git clone` the repository | [§10.1](#101-first-commit-from-the-zip) | Folder `onlywheels/` |
| 3 | PostgreSQL | [§2](#2-postgresql--pick-one-option) | A `DATABASE_URL` |
| 4 | Backend first run: `.env`, `uv sync`, `makemigrations`, `migrate`, `seed_demo`, tests | [§3](#3-backend-django) | API on :8000, `uv.lock` + migrations created |
| 5 | Frontend first run (second terminal, Django keeps running): `.env.local`, `pnpm install`, checks, `pnpm api:generate` | [§4](#4-frontend-react--vite) | App on :5173, `pnpm-lock.yaml` + generated client created |
| 6 | `git init` and commit everything (incl. the generated files) | [§10.1](#101-first-commit-from-the-zip) | Clean `git status` |
| 7 | Create the GitHub repository and push | [§10.2](#102-github-repository-and-the-first-ci-run) | CI runs and is green |
| 8 | Add the teammate, protect `main` | [§10.3](#103-teammate-and-branch-protection) | Changes only via reviewed pull requests |
| 9 | Optional: Google login, Stripe test mode, Docker | [§5](#5-google-login-optional-until-needed), [§6](#6-payments), [DEPLOYMENT.md §3.5](DEPLOYMENT.md#35-trying-the-production-stack-locally) | — |

### 0.1 Second developer – joining the existing repository

The repository already contains everything the first developer created once: migrations, `backend/uv.lock`,
`frontend/pnpm-lock.yaml`, the generated API client and the CI workflow. Only machine-specific things are
missing after cloning: the secret files `backend/.env` and `frontend/.env.local` (never committed), the
installed packages (`.venv`, `node_modules`) and a database – each developer has their own.

| # | What | Details |
|---|---|---|
| 1 | Accept the collaborator invitation (e-mail or github.com → notifications) | [§10.3](#103-teammate-and-branch-protection) |
| 2 | Install the tools | [§1](#1-tools-one-time) |
| 3 | `git clone https://github.com/<owner>/onlywheels.git` and `cd onlywheels` | — |
| 4 | PostgreSQL: Docker (option A) or native install (option B) | [§2](#2-postgresql--pick-one-option) |
| 5 | Backend (commands below) | [§3](#3-backend-django) |
| 6 | Frontend (second terminal, commands below) | [§4](#4-frontend-react--vite) |

```powershell
# terminal 1
cd backend
Copy-Item .env.example .env          # then edit DATABASE_URL and DJANGO_SECRET_KEY (own values)
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py createsuperuser
uv run python manage.py runserver

# terminal 2
cd frontend
Copy-Item .env.example .env.local
pnpm install
pnpm dev                             # http://localhost:5173
```

**Do not** run `git init`, `makemigrations` (only when you change a model yourself), or create a new GitHub
repository – that was done once. `pnpm api:generate` is only needed after a backend API change.

Keeping up to date with the teammate's work:

```powershell
git switch main
git pull
cd backend;  uv sync; uv run python manage.py migrate    # new dependencies / migrations
cd ..\frontend; pnpm install                              # new dependencies
```

Then work on a branch and open a pull request ([§10.3](#103-teammate-and-branch-protection)).

## 1. Tools (one time)

| Tool | Version | Windows install |
|---|---|---|
| Git | any recent | `winget install Git.Git` |
| Python | 3.12+ | `winget install Python.Python.3.12` |
| uv (Python packages) | latest | `winget install astral-sh.uv` |
| Node.js | 20.19+ / 22 LTS | `winget install OpenJS.NodeJS.LTS` |
| pnpm | 10 (pinned) | `corepack enable pnpm` (run after installing Node) – then `pnpm` automatically uses the version pinned in `frontend/package.json` (`packageManager`), the same one CI and Docker use. Without corepack: `npm install -g pnpm@10` |
| PostgreSQL | 16 | see step 2 |
| Stripe CLI | latest | needed from phase E – `winget install Stripe.StripeCLI` |
| Docker Desktop | optional | `winget install Docker.DockerDesktop` – only for PostgreSQL option A or to try the production stack (free for personal and education use) |

Check: `git --version`, `uv --version`, `node --version`, `pnpm --version`.

Also needed: a free **GitHub account** (students: apply for the free
[GitHub Student Developer Pack](https://education.github.com/pack), which includes GitHub Pro).

Recommended VS Code extensions: Python, Pylance, Ruff, ESLint, Tailwind CSS IntelliSense.

## 2. PostgreSQL – pick one option

All options end with a `DATABASE_URL` in `backend/.env`.

### Option A – Docker (simplest if Docker Desktop is available)

```powershell
docker compose -f infra/docker-compose.yml up -d
```

`DATABASE_URL=postgres://onlywheels:onlywheels@localhost:5432/onlywheels`

### Option B – Native Windows install

1. `winget install PostgreSQL.PostgreSQL.16` (remember the password you set for the `postgres` user).
2. Open **SQL Shell (psql)** and run:

   ```sql
   CREATE USER onlywheels WITH PASSWORD 'onlywheels' CREATEDB;
   CREATE DATABASE onlywheels OWNER onlywheels;
   ```

   `CREATEDB` is needed because the test runner creates a temporary `test_onlywheels` database.

`DATABASE_URL=postgres://onlywheels:onlywheels@localhost:5432/onlywheels`

### Option C – Supabase (hosted, free tier)

1. Create a project at supabase.com (region: EU Central).
2. **Project Settings → Database → Connection string → Session pooler**, copy the URI.
3. Append `?sslmode=require`.

`DATABASE_URL=postgres://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require`

> Each developer should use their own database (local or own Supabase project) so migrations don't clash.

## 3. Backend (Django)

```powershell
cd backend
Copy-Item .env.example .env          # then edit DATABASE_URL and DJANGO_SECRET_KEY
uv sync                              # creates .venv and installs dependencies
uv run python manage.py makemigrations   # first time only (creates migrations for all apps), then commit
uv run python manage.py migrate
uv run python manage.py seed_demo    # demo cars + fitment, products + photos + stock, garages, vouchers (safe to re-run)
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Generate a secret key: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`

| URL | What |
|---|---|
| http://127.0.0.1:8000/admin/ | Back-office (Django Admin / unfold) |
| http://127.0.0.1:8000/api/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/schema/ | OpenAPI schema (input for orval) |
| http://127.0.0.1:8000/api/v1/health/ | Health check |

Checks (the same ones CI runs):

```powershell
uv run ruff check .
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py spectacular --validate --fail-on-warn --file schema.yml
uv run pytest
```

`uv run ruff format .` formats the code; it is not enforced by CI.

## 4. Frontend (React + Vite)

```powershell
cd frontend
Copy-Item .env.example .env.local
pnpm install
pnpm dev                 # http://localhost:5173  (proxies /api and /media to Django)
```

Checks (the same ones CI runs):

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

### Generated API client

With Django running:

```powershell
pnpm api:generate        # writes src/api/generated/ (typed hooks + MSW mocks)
```

Re-run after every backend API change and commit the result, so the frontend developer
always builds against the current contract.

### Adding shadcn/ui components

```powershell
pnpm dlx shadcn@latest add dialog select tabs sheet
```

## 5. Google login (optional until needed)

1. https://console.cloud.google.com → create a project “OnlyWheels”.
2. **APIs & Services → OAuth consent screen**: External, app name, support email; add your team as test users.
3. **Credentials → Create credentials → OAuth client ID → Web application**.
   - Authorized JavaScript origins: `http://localhost:5173` and `http://localhost`
   - No redirect URIs are needed (Google Identity Services popup).
4. Copy the client ID into both:
   - `backend/.env` → `GOOGLE_OAUTH_CLIENT_ID=...`
   - `frontend/.env.local` → `VITE_GOOGLE_CLIENT_ID=...`

The “Continue with Google” button only appears when `VITE_GOOGLE_CLIENT_ID` is set.

### Real car database – all European cars (optional)

Without a key the car selector only has the 13 demo cars from `seed_demo`. With a free
[Wheel-Size](https://developer.wheel-size.com/) key it lists every make/model/generation sold in Europe,
with real factory fitment (PCD, center bore, offsets, OEM tyre sizes).

1. Sign up at https://developer.wheel-size.com/ and request the **Sandbox** plan (free, approved manually within a few hours).
2. `backend/.env` → `WHEEL_SIZE_API_KEY=<your key>` and restart Django.

How it works (`backend/apps/vehicles/wheelsize.py`): nothing is downloaded in bulk. The first time somebody opens
a make, model or generation, the backend asks Wheel-Size once and stores the answer in our tables; afterwards it is
served from the database (refreshed after 30 days). This keeps us inside the Sandbox limit of **300 requests/day**.
If the API is down or the quota is used up, the shop keeps working with what is already stored.
Imported data is visible (and editable) in the admin under Vehicles.

> The Sandbox licence is for development/testing only – a public shop needs a paid plan.

## 6. Payments

### Without any account (default)

`PAYMENT_PROVIDER=fake`: “Pay online” opens a demo page in the app with a
“Simulate successful payment” button. Everything after that (stock, fitting slot, emails) works
exactly like with a real payment. Not allowed in production settings.

Demo vouchers from `seed_demo`: `BINEAIVENIT10` (10% over 500 RON), `ROTI100` (100 RON over 2000 RON).

### Stripe (test mode)

1. Create a Stripe account (test mode is enough) and copy the **secret key** (`sk_test_...`).
2. `stripe login`, then `stripe listen --forward-to localhost:8000/api/v1/payments/webhook/stripe/`
   and copy the printed `whsec_...` secret.
3. In `backend/.env`: `PAYMENT_PROVIDER=stripe`, `STRIPE_SECRET_KEY=sk_test_...`, `STRIPE_WEBHOOK_SECRET=whsec_...`.
4. Test card: `4242 4242 4242 4242`, any future date, any CVC.

### NETOPIA (sandbox)

1. Create a NETOPIA sandbox merchant account and obtain its API key, POS signature, RSA public key, and allowed POS signatures from NETOPIA. Do not use live credentials for local testing.
2. Set these server-side values in `backend/.env`:
   - `PAYMENT_PROVIDER=netopia`
   - `NETOPIA_MODE=sandbox`
   - `NETOPIA_API_KEY` and `NETOPIA_POS_SIGNATURE`
   - `NETOPIA_PUBLIC_KEY` (PEM public key; represent line breaks as `\n` in a single-line `.env` value)
   - `NETOPIA_POS_SIGNATURE_SET` (comma-separated allowlist of POS signatures accepted in callback tokens)
   - `NETOPIA_NOTIFY_URL=https://<public-host>/api/v1/payments/webhook/netopia/`
3. NETOPIA must be able to reach the callback over public HTTPS. For local testing, expose the backend with a trusted HTTPS tunnel and use that tunnel URL in `NETOPIA_NOTIFY_URL`; keep the backend running while testing.
4. Apply migrations with `uv run python manage.py migrate`, start the backend and frontend as in §3–4, then place an order and complete it using NETOPIA's sandbox payment details. Confirm the authenticated callback changes the payment/order state; the browser redirect alone is not proof of payment.

The checkout sends `payment.options.installments=0`; it does not present a separate installment-count selector. The callback stores any installment count NETOPIA reports. Confirm how NETOPIA applies this option and which terms are eligible for your sandbox merchant/card setup before offering installments to customers.

For production, use a publicly reachable production HTTPS callback, the live API key/POS signature/public key, and `NETOPIA_MODE=live`. Switch `PAYMENT_PROVIDER=netopia` only after a sandbox checkout and callback have been verified end to end. Keep all credentials in the deployment secret store, never in frontend variables or source control.

## 7. Garage partner access

1. Create a user, tick **Staff status** and add it to the `garage_partner` group (created by `seed_demo`).
2. Open the garage in the admin and add the user to **Partner users**.
3. The partner logs in at `/admin/` and only sees (and confirms) appointments for that garage.

## 8. Unpaid orders

Stock is reserved for `ORDER_RESERVATION_MINUTES` (30). Expired orders are cancelled automatically
when new orders are placed; Celery Beat runs it every 5 minutes once Redis is used.
Manually: `uv run python manage.py expire_orders`.

## 9. Optional services (production plumbing)

Everything below is already in the code and **off by default**; development needs none of it.
Variables go in `backend/.env` (or `frontend/.env.local` for `VITE_*`); the full list is in the `.env.example` files.

| Service | Variables | What changes |
|---|---|---|
| Sentry (errors) | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`; frontend `VITE_SENTRY_DSN` | Django/Celery/React errors are reported; the browser SDK is only downloaded when the DSN is set |
| Logs | `LOG_FORMAT=json` or `console`, `LOG_LEVEL` | One JSON object per line (default when `DJANGO_DEBUG=False`) |
| Content-Security-Policy | `CSP_ENABLED=True` | CSP header on Django pages (admin, `/api/docs/`). Tests always run with it on. |
| Redis | `CACHE_URL=rediscache://localhost:6379/1`, `CELERY_BROKER_URL=redis://localhost:6379/0`, `CELERY_TASK_ALWAYS_EAGER=False` | Shared cache/rate limits; run `celery -A config worker` and `celery -A config beat` |
| SmartBill invoicing | `SMARTBILL_ENABLED`, `SMARTBILL_USER`, `SMARTBILL_TOKEN`, `SMARTBILL_CIF`, `SMARTBILL_SERIES`, `SMARTBILL_TAX_NAME`, `SMARTBILL_MEASURING_UNIT` | Paid orders enqueue invoice issuance; see below before enabling |
| Courier AWB | `SHIPPING_CARRIER`, `SHIPPING_MODE`, `SAMEDAY_*` or `FAN_COURIER_*` | Courier orders get an AWB when staff mark them "processing"; see below |
| AI photo studio | `AI_STUDIO_PROVIDER`, `REPLICATE_API_TOKEN` or `FAL_KEY`, `AI_STUDIO_DAILY_*` | Signed-in customers render wheels on a photo of their car; see below |
| Email (Resend) | `EMAIL_BACKEND=anymail.backends.resend.EmailBackend`, `RESEND_API_KEY` | Real emails instead of the console |
| File storage (R2/S3/MinIO) | `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_CUSTOM_DOMAIN` | Uploads (product photos, GLB models) go to the bucket |

### SmartBill invoicing

Invoice issuance is disabled by default. SmartBill's documented V1 API has no verified sandbox in this integration: API-created invoices consume the account's document allowance. Do not enable it until the merchant confirms an account suitable for test issuance.

Set the exact account values in `backend/.env` (or the deployment secret store):

```dotenv
SMARTBILL_ENABLED=True
SMARTBILL_API_BASE_URL=https://ws.smartbill.ro/SBORO/api
SMARTBILL_USER=<SmartBill account email>
SMARTBILL_TOKEN=<SmartBill API token>
SMARTBILL_CIF=<company tax identifier>
SMARTBILL_SERIES=<invoice series configured in SmartBill>
SMARTBILL_TAX_NAME=<exact SmartBill tax name>
SMARTBILL_MEASURING_UNIT=<exact SmartBill unit, e.g. buc>
```

Confirm the tax name, unit, series, VAT treatment and a test customer with the accountant/merchant before enabling. Once enabled, the paid-order transaction queues issuance after commit. In production, set `CELERY_TASK_ALWAYS_EAGER=False` and keep the Celery worker running; local eager mode runs the task inline. If enqueueing fails, the order remains paid and a pending invoice stays available for a staff retry; the enqueue error is logged.

**Demo invoice (no SmartBill account).** While `SMARTBILL_ENABLED=False`, setting `SMARTBILL_DEMO=True` makes every paid order get a local mock-up invoice instead of a failed one. The mock-up is laid out like a SmartBill invoice (series `DEMO`, number = order number). It carries a "DEMO" watermark and a red banner saying the official SmartBill API is disabled and that it is **not a fiscal document**. No HTTP request is made, and nothing is sent to SmartBill or ANAF. The order page shows the same notice next to the download button. `SMARTBILL_DEMO` defaults to `True` in development and `False` elsewhere, and production settings refuse to start if it is set. To convert an older failed invoice, run the "Retry pending/failed invoice" admin action. Demo invoices stay as they are after the real API is enabled. Only orders paid after that point get real SmartBill invoices.

The customer sees invoice status and a download button on the order page. Invoice metadata is available at `GET /api/v1/invoices/{order_number}/`; the PDF endpoint is `GET /api/v1/invoices/{order_number}/pdf/` and requires the order owner or staff authentication. PDFs are kept in the private invoice volume and are not served from the public media URL. Staff can retry pending/failed issuance or PDF retrieval from Django Admin. If an issuance remains in `issuing` for over 30 minutes, staff can move it to `review_required`; search SmartBill by order number and reconcile the provider result before changing state or retrying. Never retry `review_required` automatically, because SmartBill may have created an invoice despite an ambiguous response.

e-Factura submission/status automation is not implemented or verified; the stored status remains `not_sent`. Require accounting/legal approval and a documented SmartBill/ANAF workflow before live use.

### Courier AWB (Sameday / FAN Courier)

Disabled by default (`SHIPPING_CARRIER` empty): orders keep the manual flow (staff use the admin "mark shipped" action).

**Demo courier (no account needed)** – for coursework and presentations set `SHIPPING_CARRIER=demo` and restart. Moving a courier order to *processing* then creates a simulated `DEMO…` AWB, marks the order shipped and stores a one-page PDF label marked *SIMULATED* (Django Admin › *Shipping › Shipments* › label link). Nothing is sent anywhere and there is no tracking link. Each tracking refresh moves the parcel one step: picked up → in transit → delivered (which completes the order). Celery Beat refreshes hourly; to demo it quickly, select the shipment in the admin and run *Refresh tracking now* three times. Production settings refuse `demo`.

**Sameday sandbox** – ask Sameday for demo API credentials (the demo host is `https://sameday-api.demo.zitec.com`), then read your pickup point and service IDs from the API (`GET /api/client/pickup-points`, `GET /api/client/services` with the `X-AUTH-TOKEN` from `POST /api/authenticate`). The pickup point is the sender/return address, configured in your Sameday account.

```dotenv
SHIPPING_CARRIER=sameday
SHIPPING_MODE=sandbox
SAMEDAY_USERNAME=<demo user>
SAMEDAY_PASSWORD=<demo password>
SAMEDAY_PICKUP_POINT_ID=<id>
SAMEDAY_SERVICE_ID=<id>
```

**FAN Courier** – FAN has no separate sandbox host; use the test account published in FAN's API documentation (or your own SelfAWB account). The sender address is the one on the FAN client account. FAN only shares its JSON API v2 spec on request: the adapter follows the commonly used endpoints (`/login`, `/intern-awb`, `/awb/label`, `/reports/awb/tracking`); confirm them against FAN's spec before going live.

```dotenv
SHIPPING_CARRIER=fan_courier
SHIPPING_MODE=sandbox
FAN_COURIER_CLIENT_ID=<client id>
FAN_COURIER_USERNAME=<user>
FAN_COURIER_PASSWORD=<password>
```

**How it works.**

- Every product variant has a *Shipping weight (kg)*. It is required: the seed sets demo values, so set real ones in admin.
- Order items keep a copy of the weight. Each wheel/tire/set unit ships as one parcel; all accessories travel together in one parcel.
- When staff mark a **courier** order "processing", a shipment is created and the AWB task runs after commit. On success the order becomes "shipped", the A4 label PDF is stored in the private volume (`PRIVATE_INVOICE_ROOT/shipping/labels/`, never public) and staff download it from *Shipping › Shipments*.
- Garage-fitting orders never get an AWB.
- Celery Beat refreshes tracking hourly (`refresh-shipment-tracking`). Statuses only move forward; carrier statuses that cannot be recognised are shown to staff but not applied. "Delivered" completes the order.
- The customer sees the carrier, the AWB, the status and a tracking link on the order page.

**Failures.**

| Shipment state | Meaning | What to do |
|---|---|---|
| `failed` | Request rejected (bad address or credentials, missing weight) or carrier unreachable; nothing was created. The order stays "processing". | Fix the cause, then use the admin action *Retry failed AWB creation*. |
| `review_required` | Timeout/5xx: the AWB may exist. | Search the order number in the carrier portal. If an AWB exists, type it in the shipment and use *Use the AWB entered manually*. Otherwise use *Retry after confirming … no AWB exists*. Never retried automatically. |
| `created` with an error | AWB exists but the label download failed. | Use the admin action *Download missing labels*. |

Carrier status names are not published by either carrier, so they are classified by keyword (RO/EN). Check the tracking in the sandbox and adjust `apps/shipping/providers/base.py` if needed. Live mode (`SHIPPING_MODE=live`) creates billable AWBs: use it only with a signed carrier contract.

### AI photo studio (Replicate / fal)

Disabled by default (`AI_STUDIO_PROVIDER` empty): `/ai-studio` tells signed-in users the studio is unavailable and creating a job returns 503. There is no fake provider, and **every generation is billed by the provider** (about $0.04 per image).

1. Create an API key: Replicate (*Account › API tokens*) or fal (*Dashboard › Keys*). Add a small prepaid balance and, if the provider offers it, a spend limit.
2. In `backend/.env`, set one of:

   ```env
   AI_STUDIO_PROVIDER=replicate
   REPLICATE_API_TOKEN=<token>
   REPLICATE_MODEL=black-forest-labs/flux-kontext-pro   # or google/nano-banana
   REPLICATE_COST_PER_IMAGE_USD=0.04                    # check the model page
   ```

   ```env
   AI_STUDIO_PROVIDER=fal
   FAL_KEY=<key>
   FAL_MODEL=fal-ai/flux-pro/kontext
   FAL_COST_PER_IMAGE_USD=0.04
   ```

3. Keep `AI_STUDIO_DAILY_QUOTA` (per user, per Bucharest day; failed jobs do not count) and `AI_STUDIO_DAILY_BUDGET_USD` (global ceiling) low while testing. Neither provider reports the price per request, so the budget uses the `*_COST_PER_IMAGE_USD` estimate: keep it equal to or above the real model price.
4. Restart the backend, sign in, open a wheel product and click *Try them on your car with AI* (or open `/ai-studio`). Upload a JPEG/PNG/WebP car photo, pick a scene and style and generate. With `CELERY_TASK_ALWAYS_EAGER=True` the request waits for the provider; with a worker it runs in the background and the page polls.

**Privacy.** Photos are re-encoded (EXIF/GPS removed, max 2048 px) and stored under `AI_STUDIO_PRIVATE_ROOT` (default `backend/private-media/ai/`) or the private bucket `AI_STUDIO_PRIVATE_BUCKET`. They are only streamed to their owner (and staff in Django Admin) with `no-store`; they are never public media. Celery Beat (`ai-studio-cleanup`, hourly) deletes jobs older than `AI_STUDIO_RETENTION_DAYS` and recovers jobs stuck for 30 minutes. Users can delete images at any time, and account export/deletion includes them. fal requests are sent with request storage disabled; Replicate deletes inputs and outputs after about an hour.

**Failures.**

| What the user sees | Likely cause | What to do |
|---|---|---|
| "AI Studio is not available right now" banner | Provider empty, unknown, or its key missing (the backend logs which) | Set `AI_STUDIO_PROVIDER` and the matching key; restart |
| "…reached its usage limit for today" (429) | `AI_STUDIO_DAILY_BUDGET_USD` reached | Wait for the next day or raise the budget |
| "…used all your AI generations for today" (429) | The user used `AI_STUDIO_DAILY_QUOTA` | Expected; resets at local midnight |
| Job failed, "not available right now. You can retry later." | Provider rejected the key or the account has no credit (401/402/403) | Check the key and the provider balance |
| Job failed, "safety filter rejected…" | The provider's moderation refused the photo/prompt | Try another photo; nothing is retried automatically |
| Job failed, "could not be generated" | Provider error, timeout or a worker that never finished | The user can press *Retry*; staff see the technical detail in *AI studio › Generations* |

The result is labelled as an AI illustration: it is not an exact product photo and does not guarantee fitment.

### 3D showroom (wheels and cars)

`/showroom` lists active wheels and shows one at a time with finish and size selectors. The default is the wheel-only view. If at least one usable car has been uploaded in Django Admin, visitors can switch to a car view; the active garage vehicle is matched when possible, otherwise the first available car is selected. The view and selected car are stored in the URL alongside the product and variant.

**Free fallback, no assets needed:** a wheel without an uploaded `.glb` is drawn in code (`frontend/src/features/showroom3d/procedural.ts` + `GenericWheel` in `ModelCanvas.tsx`). Diameter, width and bolt pattern come from the selected variant, the finish colours the rim, and the spoke count (5/6/7/9/10) is picked per product from its slug. A "Generic 3D preview" banner tells the visitor the spoke design is indicative. Uploading a real model (steps below) replaces the generic wheel for that product only.

1. Get a wheel model whose licence allows **commercial use on a website** (manufacturer/supplier asset, or a paid/CC-BY model). Keep the licence and the author credit with your records; `Model3D` has no credit field, so if the licence requires visible attribution, add it to the product description.
2. Export it as **glTF binary (`.glb`)**, **Draco-compressed** (e.g. `gltf-transform draco in.glb out.glb`), wheel **centred at the origin**, **1 unit = 1 m**, axle along Z (facing the camera). Aim for under ~3 MB.
3. Name the materials: the paintable rim surface `rim` or `finish` (any name containing those words). If no material is named so, everything except `tire`/`tyre`/`rubber`/`logo`/`badge`/`emblem`/`valve`/`glass` is painted.
4. Django Admin › *Catalog › Products* › the wheel › *3D model* inline: upload the `.glb`, optionally a thumbnail and `finish_materials`, e.g.

   ```json
   {"black": {"color": "#202020", "metalness": 0.6, "roughness": 0.35}}
   ```

   Keys are variant finishes (`silver`, `black`, `bronze`, `gunmetal`, `chrome`, `white`). Missing finishes or fields use built-in defaults; invalid colours or values outside 0–1 are ignored.
5. Open `/showroom` (or `/showroom?product=<slug>`), rotate the wheel and switch finishes.

#### Add car models

Car files are **not shipped with the project**. You must obtain a model and upload it yourself; suitable free models may be downloaded from sources such as Sketchfab, subject to the individual model's licence and download terms. Use only a licence that permits commercial use and modification (for example CC0, CC-BY or CC-BY-SA); do not use NC or no-derivatives models. Prefer generic, unbranded cars: a model-file licence may not grant rights to vehicle logos or other trademarks. Keep a record of the licence and author, and enter the required credit and source URL in the admin so visitors can see the attribution.

1. Prepare a `.glb` car model. Set its nose direction (`front`) correctly; the model is uniformly scaled in the viewer to the entered real vehicle length, so note the model's length axis and export orientation. Keep descriptive wheel/tire node names and POSITION accessor bounds in the file; these help automatic anchor detection. Draco-compress the model (for example, `gltf-transform draco in.glb out.glb`).
2. In Django Admin, open **Catalog › 3D car models** and add a car. Enter its name/body type, real length in metres, nose direction, optional matching vehicle model, attribution and source URL. Upload the GLB and save.
3. On save, the admin attempts to detect the four road-wheel positions from named GLB parts and their POSITION bounds. The car is offered in the showroom only after detection succeeds or manual positions are supplied. If detection fails (for example, names or bounds are missing), use the displayed message and enter `wheel_anchors` as JSON with exactly four points in the GLB's original coordinates, for example:

   ```json
   {
     "axis": "x",
     "wheels": [
       {"x": -1.2, "y": 0.3, "z": -0.7},
       {"x": -1.2, "y": 0.3, "z": 0.7},
       {"x": 1.2, "y": 0.3, "z": -0.7},
       {"x": 1.2, "y": 0.3, "z": 0.7}
     ]
   }
   ```

   `axis` is the car's length axis (`x` or `z`); `y` is up. Manual positions override automatic detection. Activate the model and use the admin's preview link to check wheel placement; deactivate it while making corrections.
4. In `/showroom`, choose **On a car** and select the model. Car-view GLBs are loaded only after this choice. If a car cannot load, retry or return to wheel-only mode.

Without WebGL, the page shows the product photo rather than a 3D scene. A product without a wheel GLB uses the generic wheel even in car view; a broken wheel GLB shows an error with *Retry*. The Draco decoder is served from the site itself (`/draco/`); this is why the CSP allows `'wasm-unsafe-eval'` and `blob:` workers. The 3D code (~300 KB gzipped) is loaded only on this page and is not precached by the PWA.
PWA: `pnpm dev` does **not** register the service worker; use `pnpm build; pnpm preview` to test install/offline.
After a new build the service worker updates itself on the next page load.

## 10. Git, GitHub and CI (one time)

### 10.1 First commit from the zip

After the backend and frontend first runs (§3, §4), so the generated files exist:

```powershell
git config --global user.name "Your Name"            # once per laptop, otherwise the commit fails
git config --global user.email "you@example.com"     # use the email of your GitHub account
cd C:\dev\onlywheels                 # the folder extracted from onlywheels.zip
git init -b main
git status                           # .env, .env.local, .venv, node_modules must NOT be listed
git add .
git commit -m "Initial import of OnlyWheels"
```

The commit must contain these files created on the first run – CI depends on them:

| File(s) | Created by |
|---|---|
| `backend/uv.lock` | `uv sync` |
| `backend/apps/*/migrations/0001_initial.py` | `makemigrations` |
| `frontend/pnpm-lock.yaml` | `pnpm install` |
| `frontend/src/api/generated/` | `pnpm api:generate` |

Secrets stay out of Git automatically (`.gitignore`): `backend/.env`, `frontend/.env.local`, `infra/.env.prod`.

### 10.2 GitHub repository and the first CI run

1. github.com → **New repository** → name `onlywheels`, Private or Public (see §10.4), **no** README,
   `.gitignore` or license (the project has them).
2. Push:

   ```powershell
   git remote add origin https://github.com/<your-user>/onlywheels.git
   git push -u origin main
   ```

   The first push opens a browser window to log in to GitHub (Git Credential Manager).
3. Repository → **Actions** tab: the **CI** workflow starts by itself (no setup needed – GitHub picks up
   `.github/workflows/ci.yml`). Jobs: `backend` and `frontend` in parallel, then `docker`.
4. Red job → open it, read the failing step, fix locally, commit, push again. Common causes and fixes:
   [DEPLOYMENT.md §6.5](DEPLOYMENT.md#65-when-ci-fails).

What each step checks: [DEPLOYMENT.md §6](DEPLOYMENT.md#6-ci--githubworkflowsciyml).

### 10.3 Teammate and branch protection

1. Repository → **Settings → Collaborators → Add people** → the other developer (write access). They then
   follow [§0.1](#01-second-developer--joining-the-existing-repository).
2. After CI was green once: **Settings → Branches → Add branch protection rule** (or **Rules → Rulesets**) for
   `main`: require a pull request with 1 approval and require the status checks `backend`, `frontend`, `docker`.
3. Daily work: `git switch -c feat/<name>` → commit → `git push -u origin feat/<name>` → open a pull request
   → CI runs → the other developer reviews → merge.

### 10.4 Does CI cost anything?

For this project: **no**, as long as nothing paid is enabled. GitHub's rules (checked October 2026):

| Repository | GitHub Actions on standard Linux runners (what `ci.yml` uses) |
|---|---|
| **Public** | Free, unlimited |
| **Private**, GitHub Free account | $12 of usage included per month ≈ **2,000 minutes** ($0.006/min) |
| **Private**, GitHub Pro (free with the Student Developer Pack) | $18 included ≈ **3,000 minutes** |

- One CI run of this project takes roughly 8–12 runner minutes in total (three jobs, estimate – check the real
  number in the Actions tab after the first runs). That is about 150–350 runs per month on a private repository.
- **Without a payment method on the account, GitHub cannot charge you**: when the included usage is used up,
  workflows simply stop until the next month. Don't add a card, or set the Actions budget to $0.
- Minutes are counted for the **repository owner** (your account), also when the teammate pushes.
- Storage: the pnpm cache uses the included 10 GB cache per repository; the workflow uploads no artifacts or
  packages, so there is no storage cost.
- Already built in to save minutes: a new push cancels the older run of the same branch, and every job stops
  after 15 minutes if something hangs.
- If minutes ever get tight on a private repository: run the `docker` job only after merges to `main`
  (add `if: github.event_name == 'push'` to that job) – it is the slowest job.
- Usage: GitHub → your avatar → **Settings → Billing and licensing → Usage**.

A public repository is fine for a university project as long as no secrets are committed (they are ignored by
`.gitignore`), but check whether your course requires the code to be private.

## Troubleshooting

| Problem | Fix |
|---|---|
| `CSRF Failed` on POST | Call the API through Vite (relative `/api/...` URLs, `VITE_API_URL` empty) and keep the frontend origin in `CSRF_TRUSTED_ORIGINS`. |
| `401` everywhere after a while | Normal: access token expires after 15 min, the frontend refreshes it automatically. If refresh fails, log in again. |
| `permission denied to create database` in tests | Give the DB user `CREATEDB` (step 2B). |
| `relation "accounts_user" does not exist` | Run `makemigrations` (see step 3) then `migrate`. |
| Catalog is empty | Run `uv run python manage.py seed_demo`. |
| `UnicodeEncodeError: 'charmap'` in the backend log after a payment (Windows) | The dev console email backend can't print Romanian characters on a cp1252 console. The order is still paid; set `$env:PYTHONUTF8 = "1"` before `runserver` to see the emails. |
| `pnpm preview` shows an old version | The service worker served the cached build; reload once more (or DevTools → Application → Service workers → Unregister). |
| Admin/Swagger broken only with `CSP_ENABLED=True` | Browser console shows the blocked URL; add it to `CONTENT_SECURITY_POLICY` in `config/settings/base.py`. |
