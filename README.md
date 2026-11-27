# OnlyWheels

Online shop for wheels, tires and complete wheel sets, with search by vehicle, a 3D showroom, an AI photo
studio and fitting at partner garages. University project (MSA).

- **Frontend:** React 19 + TypeScript + Vite, React Router 7, TanStack Query, Orval OpenAPI client, Three.js (`@react-three/fiber` + `@react-three/drei`), Tailwind 4 + shadcn/ui, i18next (ro/en), Capacitor 8 Android (`ro.onlywheels.app`)
- **Backend:** Python 3.12+ + Django 5 + Django REST Framework, dual JWT auth (httpOnly cookies + CSRF on web, Bearer JWT + Android Keystore on Capacitor), Celery + Beat (eager in dev, Redis in prod)
- **Database:** PostgreSQL 16

## Repository

```
frontend/   React SPA/PWA + Capacitor 8 Android app (`frontend/android/`)
backend/    Django REST API + Unfold admin back-office
infra/      docker-compose for local PostgreSQL, production Docker images + compose + nginx
docs/       architecture, prototype, setup, Android guide, API conventions, deployment, roadmap
.github/    CI workflow (backend, frontend, Docker build)
```

Details: [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) · Architecture: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) · Android: [docs/ANDROID.md](docs/ANDROID.md) · **Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)**

## Getting started

For an already-configured laptop, see [QUICKSTART.md](QUICKSTART.md). For first-time machine setup, follow [docs/SETUP.md](docs/SETUP.md) (and [docs/ANDROID.md](docs/ANDROID.md) for the Android debug build). Short version:

```powershell
# 1. PostgreSQL (Docker Desktop)
docker compose -f infra\docker-compose.yml up -d

# 2. Backend
cd backend; Copy-Item .env.example .env; uv sync
uv run python manage.py migrate; uv run python manage.py seed_demo
uv run python manage.py runserver

# 3. Frontend (second terminal)
cd frontend; Copy-Item .env.example .env.local; pnpm install; pnpm dev
```

Open http://localhost:5173.

## Working together

- API rules: [docs/api/CONVENTIONS.md](docs/api/CONVENTIONS.md)
- Branches: `main` is always runnable; work on `feat/<short-name>` / `fix/<short-name>` and merge via pull request reviewed by the other developer.
- Before pushing: backend `uv run pytest && uv run ruff check .`, frontend `pnpm typecheck && pnpm lint && pnpm test`.
- Never commit `.env` files or real keys.

## Status

| Phase | Scope | State |
|---|---|---|
| A | Repo layout, setup docs, API conventions | done |
| B | Django foundation: settings, core, custom user, web cookie JWT + native Bearer JWT auth, Google login, password reset, addresses | done |
| C | React foundation: responsive layout, routing, i18n, generated Orval API client, auth pages, mobile filter sheet & skeletons | done |
| D | Vehicles (Wheel-Size read-through + stale-while-revalidate sync), declarative fitment engine, catalog, stock, favorites, saved vehicles, demo seed data | done |
| E | Cart (guest + account bulk merge, integer minor-unit `bani` math), checkout, vouchers (reservation + rollback), payments (`fake`, Stripe, NETOPIA, COD, pay-at-garage), orders, scoped reservation expiry, garage fitting slots | done |
| F | Reviews with moderation, order/garage emails, admin actions (orders, appointments, reviews), partner garage access | done |
| G | Phase-2 features: 3D wheel & car showroom (`/showroom`), AI photo studio (`/ai-studio`, Replicate/fal), SmartBill + demo PDF invoicing, Sameday/FAN Courier + demo AWB shipping | done (live providers env-switched) |
| H | Production readiness: Sentry, structlog, CSP, WhiteNoise, R2/S3, Redis cache, Resend email, web PWA, lazy routes, GDPR export/delete, Dockerfiles + prod compose + nginx, GitHub Actions CI | done |
| I | Android app (Capacitor 8): `frontend/android` (`ro.onlywheels.app`), Keystore token cache (`@aparajita/capacitor-secure-storage`), in-app fake checkout + `onlywheels://checkout/success` deep-link return, Service Worker exclusion on native builds | done (pending physical device/emulator demo run per [ANDROID.md](docs/ANDROID.md)) |
