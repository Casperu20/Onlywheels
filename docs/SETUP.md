# Development setup

Everything below runs on the **development machine**. This repository only contains source and config;
nothing has to be installed globally except the tools in step 1.

## 1. Tools (one time)

| Tool | Version | Windows install |
|---|---|---|
| Git | any recent | `winget install Git.Git` |
| Python | 3.12+ | `winget install Python.Python.3.12` |
| uv (Python packages) | latest | `winget install astral-sh.uv` |
| Node.js | 20.19+ / 22 LTS | `winget install OpenJS.NodeJS.LTS` |
| pnpm | 10+ | `corepack enable pnpm` (run after installing Node) |
| PostgreSQL | 16 | see step 2 |
| Stripe CLI | latest | needed from phase E – `winget install Stripe.StripeCLI` |

Check: `git --version`, `uv --version`, `node --version`, `pnpm --version`.

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
uv run python manage.py seed_demo    # demo cars + fitment, products + stock, garages, vouchers (safe to re-run)
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

Checks:

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## 4. Frontend (React + Vite)

```powershell
cd frontend
Copy-Item .env.example .env.local
pnpm install
pnpm dev                 # http://localhost:5173  (proxies /api and /media to Django)
```

Checks:

```powershell
pnpm typecheck
pnpm lint
pnpm test
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
| Email (Resend) | `EMAIL_BACKEND=anymail.backends.resend.EmailBackend`, `RESEND_API_KEY` | Real emails instead of the console |
| File storage (R2/S3/MinIO) | `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_CUSTOM_DOMAIN` | Uploads (product photos, GLB models) go to the bucket |

PWA: `pnpm dev` does **not** register the service worker; use `pnpm build; pnpm preview` to test install/offline.
After a new build the service worker updates itself on the next page load.

## Troubleshooting

| Problem | Fix |
|---|---|
| `CSRF Failed` on POST | Call the API through Vite (relative `/api/...` URLs, `VITE_API_URL` empty) and keep the frontend origin in `CSRF_TRUSTED_ORIGINS`. |
| `401` everywhere after a while | Normal: access token expires after 15 min, the frontend refreshes it automatically. If refresh fails, log in again. |
| `permission denied to create database` in tests | Give the DB user `CREATEDB` (step 2B). |
| `relation "accounts_user" does not exist` | Run `makemigrations` (see step 3) then `migrate`. |
| Catalog is empty | Run `uv run python manage.py seed_demo`. |
| `pnpm preview` shows an old version | The service worker served the cached build; reload once more (or DevTools → Application → Service workers → Unregister). |
| Admin/Swagger broken only with `CSP_ENABLED=True` | Browser console shows the blocked URL; add it to `CONTENT_SECURITY_POLICY` in `config/settings/base.py`. |
