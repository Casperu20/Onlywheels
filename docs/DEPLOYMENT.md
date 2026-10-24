# Deployment (own domain)

Target: a small, cheap production setup for the project demo with a real domain, e.g. `onlywheels.ro`.
Nothing here is automated yet (Docker/CI come later); this is the agreed plan.

## Topology

```
onlywheels.ro      → Cloudflare Pages      (frontend: static build of `frontend/`)
api.onlywheels.ro  → VPS (Hetzner/DO) or Render/Railway   (Django + Gunicorn/Uvicorn)
                     ├── PostgreSQL (managed: Supabase / Neon / provider DB)
                     ├── Redis (Celery broker) + Celery worker + Celery Beat
                     └── media → Cloudflare R2 (S3-compatible)
DNS + TLS + WAF    → Cloudflare
```

## 1. Domain and DNS

1. Buy the domain (ROTLD registrar for `.ro`), set the nameservers to Cloudflare.
2. DNS records: `onlywheels.ro` → Cloudflare Pages project, `api` → server IP (proxied, orange cloud).
3. SSL/TLS mode **Full (strict)**; enable "Always use HTTPS".

## 2. Backend

Environment (`backend/.env` on the server, never in git):

```
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<long random>
DJANGO_ALLOWED_HOSTS=api.onlywheels.ro
DATABASE_URL=postgres://...?sslmode=require
FRONTEND_URL=https://onlywheels.ro
CORS_ALLOWED_ORIGINS=https://onlywheels.ro
CSRF_TRUSTED_ORIGINS=https://onlywheels.ro
CSRF_COOKIE_DOMAIN=.onlywheels.ro          # SPA must read the csrftoken cookie set by the API
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False
EMAIL_BACKEND=anymail / SMTP provider (Resend, SendGrid…)
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_... (or sk_test_ for the demo)
STRIPE_WEBHOOK_SECRET=whsec_...
GOOGLE_OAUTH_CLIENT_ID=...
```

Steps on a VPS (Ubuntu):

1. `uv sync --no-dev`, `uv run python manage.py migrate`, `collectstatic`, `createsuperuser`.
2. Processes (systemd units or Docker later):
   - `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -w 3 -b 127.0.0.1:8000`
   - `celery -A config worker -l info`
   - `celery -A config beat -l info` (expires unpaid orders every 5 min)
3. Nginx in front: TLS from Cloudflare Origin Certificate, `client_max_body_size 10m`,
   proxy `/` to Gunicorn, serve `/static/` from `staticfiles/`.
4. Media: add `django-storages[s3]` with Cloudflare R2 credentials (`AWS_S3_ENDPOINT_URL`, bucket, keys)
   before allowing uploads in production.
5. Stripe dashboard → Webhooks → `https://api.onlywheels.ro/api/v1/payments/webhook/stripe/`
   with events `checkout.session.completed`, `checkout.session.async_payment_succeeded`,
   `checkout.session.async_payment_failed`, `checkout.session.expired`.
6. Google Cloud OAuth client: add `https://onlywheels.ro` to Authorized JavaScript origins.

`config/settings/prod.py` already enforces HTTPS redirects, HSTS, secure cookies and refuses
`PAYMENT_PROVIDER=fake`.

## 3. Frontend

Cloudflare Pages project connected to the repository:

- Root directory `frontend`, build command `pnpm install && pnpm build`, output `dist`.
- Environment: `VITE_API_URL=https://api.onlywheels.ro`, `VITE_GOOGLE_CLIENT_ID=...`.
- SPA routing: add `frontend/public/_redirects` with `/* /index.html 200`.

Cookies: the API sets `ow_access`/`ow_refresh` (httpOnly, Secure, SameSite=Lax) for `api.onlywheels.ro`;
both sites are the same "site" (`onlywheels.ro`), so Lax cookies are sent with the SPA's requests.

## 4. Before going live (checklist)

- [ ] `DEBUG=False`, real `SECRET_KEY`, admin user with a strong password (+ 2FA later).
- [ ] Database backups (daily dump + provider PITR) and a tested restore.
- [ ] Sentry DSN for Django and React; uptime check on `/api/v1/health/`.
- [ ] Legal pages: terms, privacy policy (GDPR), cookies, ANPC/SOL links (required in Romania).
- [ ] Replace demo fitment/catalog data and remove the "demo" labels.
- [ ] Real invoicing (SmartBill, phase 2) before accepting real payments.

## 5. Later: containers + CI

`infra/docker-compose.yml` already defines PostgreSQL for development. Next steps:
one `backend.Dockerfile` (web/worker/beat = same image, different command), GitHub Actions
running `pytest` + `pnpm test` + `pnpm build` on every pull request, then deploy on merge to `main`.
