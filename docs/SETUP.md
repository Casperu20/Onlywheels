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

The second developer only does steps 1, 3, 4 and 5 after cloning (`git clone`, no `git init`), without
`makemigrations` (the migrations are already committed).

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

1. Repository → **Settings → Collaborators → Add people** → the other developer (write access).
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
| `pnpm preview` shows an old version | The service worker served the cached build; reload once more (or DevTools → Application → Service workers → Unregister). |
| Admin/Swagger broken only with `CSP_ENABLED=True` | Browser console shows the blocked URL; add it to `CONTENT_SECURITY_POLICY` in `config/settings/base.py`. |
