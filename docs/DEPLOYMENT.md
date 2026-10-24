# Deployment (own domain)

Target: a small, cheap production setup for the project demo with a real domain, e.g. `onlywheels.ro`.
Two ways are prepared; pick one.

| | Option A – one server with Docker | Option B – managed services |
|---|---|---|
| Frontend | nginx container (same domain) | Cloudflare Pages |
| API | gunicorn container | Render / Railway / VPS |
| Database | PostgreSQL container (or managed) | Managed PostgreSQL (Supabase, Neon…) |
| Jobs | Redis + Celery worker + beat containers | Provider's Redis + worker/cron |
| Effort | One `docker compose up`, you run backups | More dashboards, less server work |
| Files | `infra/docker-compose.prod.yml`, `infra/docker/`, `infra/nginx/` | `frontend/public/_headers`, `_redirects` |

> The Docker images and the compose file were written but **not yet built or run** (no Docker on the
> development laptop). Build them once on a machine with Docker; the CI workflow also builds them.

## 1. Domain and DNS (both options)

1. Buy the domain (ROTLD registrar for `.ro`), set the nameservers to Cloudflare.
2. Option A: `onlywheels.ro` (and `www`) → server IP, proxied (orange cloud).
   Option B: `onlywheels.ro` → Cloudflare Pages project, `api` → API host.
3. SSL/TLS mode **Full (strict)** (Cloudflare Origin Certificate on the server) and "Always use HTTPS".

## 2. Option A – single server with Docker Compose

```
Cloudflare (TLS) ──► nginx container :80
                       ├── /            React build (SPA, service worker)
                       ├── /api/ /admin/ /static/ ──► web (gunicorn, Django, WhiteNoise)
                       └── /media/      shared volume (or Cloudflare R2)
                     worker + beat (Celery)  ──► redis
                     postgres (volume postgres-data)
```

On a VPS (Ubuntu with Docker Engine + compose plugin):

```bash
git clone <repo> onlywheels && cd onlywheels
cp infra/.env.prod.example infra/.env.prod          # fill in every value
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod up -d --build
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod exec web python manage.py createsuperuser
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod exec web python manage.py seed_demo   # demo only
```

- `web` runs `migrate` on every start, then gunicorn. `worker` and `beat` use the same image.
- Static files are collected into the image at build time and served by WhiteNoise.
- Uploads go to the `media` volume (served by nginx) unless `AWS_STORAGE_BUCKET_NAME` is set (R2).
- Same origin for SPA and API → no CORS, `VITE_API_URL` stays empty, cookies are first-party.
- TLS ends at Cloudflare; nginx forwards `X-Forwarded-Proto` so Django's HTTPS redirect does not loop.
  Without Cloudflare, put Caddy or Traefik in front for certificates.
- Update: `git pull` then the same `up -d --build` command.
- Backups: `docker compose … exec postgres pg_dump -U onlywheels onlywheels > backup.sql` daily (cron),
  copy off the server; test a restore.

## 3. Option B – Cloudflare Pages + hosted API

```
onlywheels.ro      → Cloudflare Pages      (frontend: static build of `frontend/`)
api.onlywheels.ro  → Render/Railway or VPS (Django + gunicorn, same Dockerfile as option A)
                     ├── PostgreSQL (managed)
                     ├── Redis + Celery worker + Celery Beat
                     └── media → Cloudflare R2
```

Backend environment: same values as `infra/.env.prod.example`, plus

```
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_ALLOWED_HOSTS=api.onlywheels.ro
DATABASE_URL=postgres://...?sslmode=require
CELERY_BROKER_URL=redis://...
CACHE_URL=rediscache://...
CELERY_TASK_ALWAYS_EAGER=False
CSRF_COOKIE_DOMAIN=.onlywheels.ro          # the SPA must read the csrftoken cookie set by the API
```

- Build the API from `infra/docker/backend.Dockerfile` (context `backend/`). Start command:
  `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
  Worker: `celery -A config worker -l info`; beat: `celery -A config beat -l info`.
- Cloudflare Pages: root directory `frontend`, build command `pnpm install && pnpm build`, output `dist`;
  environment `VITE_API_URL=https://api.onlywheels.ro`, `VITE_GOOGLE_CLIENT_ID`, `VITE_SENTRY_DSN`.
- `frontend/public/_redirects` (SPA routing) and `frontend/public/_headers` (security headers + CSP) are
  picked up by Pages automatically. **Edit the `connect-src` in `_headers`** if the API domain differs from
  `https://api.onlywheels.ro`.
- Cookies: `ow_access`/`ow_refresh` (httpOnly, Secure, SameSite=Lax) are set for `api.onlywheels.ro`; both
  hosts are the same "site" (`onlywheels.ro`), so the browser sends them with the SPA's requests.

## 4. External services (both options)

| Service | What to do | Variables |
|---|---|---|
| Stripe | Dashboard → Webhooks → `https://<api host>/api/v1/payments/webhook/stripe/`, events `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired` | `PAYMENT_PROVIDER=stripe`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| Google login | OAuth client → add `https://onlywheels.ro` to Authorized JavaScript origins | `GOOGLE_OAUTH_CLIENT_ID`, `VITE_GOOGLE_CLIENT_ID` |
| Resend (email) | Verify the domain (SPF/DKIM DNS records), create an API key | `EMAIL_BACKEND=anymail.backends.resend.EmailBackend`, `RESEND_API_KEY`, `DEFAULT_FROM_EMAIL` |
| Cloudflare R2 | Create a bucket + API token; optional public custom domain `media.onlywheels.ro` | `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_CUSTOM_DOMAIN` |
| Sentry | Two projects: Django and React | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `VITE_SENTRY_DSN` (build-time) |
| Uptime | Any monitor on `/api/v1/health/` | — |

`config/settings/prod.py` enforces HTTPS redirects, HSTS, secure cookies, WhiteNoise compressed static files and
refuses `PAYMENT_PROVIDER=fake`. With `DEBUG=False`, logs are JSON and the CSP header is on for Django pages.

## 5. CI

`.github/workflows/ci.yml` runs on every push to `main` and every pull request:

- **backend** – PostgreSQL 16 service, `uv sync --locked`, ruff, `makemigrations --check`, strict OpenAPI
  validation, pytest;
- **frontend** – `pnpm install --frozen-lockfile`, typecheck, lint, Vitest, production build;
- **docker** – builds both production images with `docker-compose.prod.yml`.

It needs the committed `uv.lock`, `pnpm-lock.yaml` and migrations ([ROADMAP.md](ROADMAP.md) step 1).
Automatic deployment on merge (e.g. SSH + `docker compose up -d --build`, or the Render deploy hook) can be added
as a fourth job once a server exists.

## 6. Before going live (checklist)

- [ ] `DEBUG=False`, real `DJANGO_SECRET_KEY` (50+ random characters), admin user with a strong password (+ 2FA later).
- [ ] `python manage.py check --deploy` shows no warnings except HSTS preload (only enable preload when sure).
- [ ] Database backups (daily dump + provider PITR) and a tested restore.
- [ ] Sentry DSNs set; uptime check on `/api/v1/health/`.
- [ ] Open the site with the browser console: no CSP violations (admin, Swagger, Google login, Sentry).
- [ ] Legal pages: terms, privacy policy (GDPR – the export/delete endpoints exist), cookies, ANPC/SOL links.
- [ ] Replace demo fitment/catalog data and remove the "demo" labels.
- [ ] Real invoicing (SmartBill, phase 2) before accepting real payments.
