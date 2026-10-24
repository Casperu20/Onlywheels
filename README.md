# OnlyWheels

Online shop for wheels, tires and complete wheel sets, with search by vehicle, a 3D showroom, an AI photo
studio and fitting at partner garages. University project (MSA).

- **Frontend:** React 19 + TypeScript + Vite, React Router 7, TanStack Query, Tailwind + shadcn/ui, i18next (ro/en)
- **Backend:** Python + Django 5 + Django REST Framework, JWT in httpOnly cookies, Celery (eager mode for now)
- **Database:** PostgreSQL

## Repository

```
frontend/   React app (web, later Android via Capacitor)
backend/    Django API + admin back-office
infra/      docker-compose for local services (PostgreSQL)
docs/       architecture, prototype, setup, API conventions
```

Details: [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) · Architecture: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) · **Next steps: [docs/ROADMAP.md](docs/ROADMAP.md)**

## Getting started

Follow [docs/SETUP.md](docs/SETUP.md) and the first-run checklist in [docs/ROADMAP.md §1](docs/ROADMAP.md#1-first-run-on-the-development-machine-do-this-first)
(the code has not been run yet). Short version:

```powershell
# backend
cd backend; Copy-Item .env.example .env; uv sync
uv run python manage.py makemigrations
uv run python manage.py migrate; uv run python manage.py seed_demo
uv run python manage.py runserver

# frontend (second terminal)
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
| B | Django foundation: settings, core, custom user, JWT cookie auth, Google login, password reset, addresses | done (needs first run) |
| C | React foundation: layout from prototype, routing, i18n, API client, auth pages | done (needs first run) |
| D | Vehicles, fitment engine, catalog, stock, favorites, saved vehicles, demo seed data | done (needs first run) |
| E | Cart (guest + account), checkout, vouchers, Stripe / simulated payment, orders, stock reservation, garage fitting slots | done (needs first run) |
| F | Reviews with moderation, order/garage emails, admin actions (orders, appointments, reviews), partner garage access | done (needs first run) |
| G | Phase-2 structure: shipping (Sameday/Fan Courier), invoicing (SmartBill), AI studio, Netopia, push, Meilisearch, 3D showroom, native adapters, [deployment notes](docs/DEPLOYMENT.md) | structure + design notes |
