# OnlyWheels – Project Structure

> Folder layout for the OnlyWheels monorepo, derived from [ARCHITECTURE.md](architecture/ARCHITECTURE.md)
> and the homepage prototype in [prototype/index.html](prototype/index.html).
> Stack: **React 19 + TypeScript + Vite (PWA → Android via Capacitor)** on the frontend,
> **Python 3.12 + Django 5 + DRF + Celery** on the backend, **PostgreSQL / Redis / S3** for data.
>
> **Section 0** shows what exists in the repository today. Sections 1–7 are the **target layout** for the whole
> roadmap; folders that don't exist yet are listed in [§0.3](#03-target-items-not-created-yet).

---

## 0. Current repository (as built)

### 0.1 Frontend (`frontend/src/`)

```
src/
├── main.tsx                       # Mounts providers + router
├── app/
│   ├── router.tsx                 # All routes (React Router 7), protected routes under <RequireAuth>
│   ├── providers.tsx              # TanStack Query, toasts (sonner), devtools
│   └── layout/                    # RootLayout, AnnouncementBar, Header, MobileNav, Footer, Logo,
│                                  # LanguageSwitcher, navigation.ts (menu items)
├── routes/                        # Pages: Home, Catalog, Product, Cart, Checkout, OrderPages (orders,
│                                  # order detail, success, fake pay, fitting), Auth, Account, AccountSubPages
│                                  # (garage, favorites), Placeholder (showroom, AI), ErrorPages
├── features/                      # Each: api.ts (types + calls), hooks, components/, index.ts
│   ├── auth/                      # Login/register/reset forms, Google button, RequireAuth, useMe
│   ├── vehicle/                   # Make→model→generation selector, active vehicle store, garage hooks
│   ├── catalog/                   # Filters (URL <-> API), product card/grid, wheel visual, fitment badge
│   ├── favorites/                 # Heart button, favorites hooks
│   ├── cart/                      # Guest store (browser), server cart hooks, merge after login
│   ├── checkout/                  # Quote (preview), create order, zod schema, saved addresses
│   ├── garages/                   # Garage cards, garage + date + slot picker
│   ├── orders/                    # Orders API, status badge, totals table
│   ├── reviews/                   # Reviews list + form, stars
│   ├── showroom3d/                # Design notes only (phase 2)
│   └── ai-studio/                 # Design notes only (phase 2)
├── api/                           # http.ts (axios: CSRF, token refresh, language), errors.ts,
│                                  # queryClient.ts, generated/ (empty until `pnpm api:generate`)
├── components/                    # FormField, PageLoader, ComingSoon, ui/ (button, input, label, native-select)
├── lib/                           # format.ts (RON), useLocale.ts, utils.ts (cn), native/ (camera, share,
│                                  # push, storage adapters for Capacitor later)
├── i18n/                          # i18next setup + locales/ro|en/common.json
├── styles/globals.css             # Tailwind 4 + brand tokens from the prototype
└── types/google.d.ts              # Google Identity Services typings
tests/unit/                        # Vitest: auth schemas, catalog filters/format, cart, checkout schema, Header
```

### 0.2 Backend (`backend/`)

```
config/                # settings/{base,dev,prod,test}.py, urls.py, celery.py (Beat: expire orders)
apps/
├── core/              # TimeStampedModel (UUID), error format, pagination, health + csrf, seed_demo
├── accounts/          # User (email), Address, cookie JWT auth, Google login, password reset
├── vehicles/          # Make/Model/Generation, UserVehicle (garage), seed_vehicles
├── fitment/           # FitmentSpec, normalize.py, services.py (fit check + DB filter)
├── catalog/           # Brand, Category, Product, ProductVariant, ProductMedia, filters, selectors,
│                      # seed_catalog, search_index.py (Meilisearch plan)
├── inventory/         # StockItem (quantity, reserved), CSV import in admin
├── pricing/           # Voucher + validation/discount, seed_vouchers
├── cart/              # Cart, CartItem, merge
├── garages/           # Garage (hours, capacity, fitting price, partner users), slots API, seed_garages
├── appointments/      # Appointment, slot calculation/holding, partner-restricted admin
├── orders/            # Order, OrderItem, OrderStatusChange, services.py (lifecycle), expire_orders
├── payments/          # Payment, WebhookEvent, providers/ (fake, stripe, netopia stub), Stripe webhook
├── notifications/     # Email tasks (order paid/status, garage booking), push.py stub
├── reviews/           # Favorite, Review (moderation), urls/{favorites,reviews}.py
├── shipping/          # Phase 2 structure: Shipment, carrier providers (Sameday, Fan Courier)
├── invoicing/         # Phase 2 structure: Invoice, SmartBill plan
└── ai_studio/         # Phase 2 structure: AIGeneration, quota, image providers (Replicate, fal.ai)
templates/emails/      # password_reset, order_confirmation, order_status, garage_booking (.txt, ro + en)
tests/                 # factories.py, test_health.py, test_seed.py (+ tests/ inside each app)
conftest.py            # api_client, user, auth_client fixtures
```

Other top-level items: `infra/docker-compose.yml` (PostgreSQL only), `docs/` (architecture, prototype,
[SETUP](SETUP.md), [API conventions](api/CONVENTIONS.md), [DEPLOYMENT](DEPLOYMENT.md), [ROADMAP](ROADMAP.md)),
`.gitignore`, `.editorconfig`, `.gitattributes`, `README.md`.

### 0.3 Target items not created yet

| Item | When |
|---|---|
| `.github/workflows/`, `scripts/`, Dockerfiles, `infra/nginx`, Redis/MinIO/Mailpit in compose | When Docker/CI are introduced |
| `frontend/android/`, `capacitor.config.ts` | Phase 3 (Android) |
| PWA (`vite-plugin-pwa`, manifest, icons) | Roadmap, see [ROADMAP.md](ROADMAP.md) |
| `features/home`, `features/fitting`, `features/account` as separate folders | Not needed: home/fitting/account are pages in `routes/` |
| Separate `search/` app | Replaced by `catalog/search_index.py` |
| `lib/analytics.ts`, `lib/sentry.ts`, `tests/e2e/` (Playwright) | Before going live |
| `docs/adr/` | Decisions are recorded in [ARCHITECTURE.md §13](architecture/ARCHITECTURE.md#13-implementation-status-as-built) |

---

## 1. Top level

```
onlywheels/
├── frontend/            # Customer app: React + Vite PWA, later wrapped as Android app (Capacitor)
├── backend/             # Django monolith: REST API, Django Admin back-office, Celery workers
├── infra/               # Docker Compose for local dev, Dockerfiles, Nginx, deployment config
├── docs/                # Architecture, diagrams, API notes, the HTML prototype
├── scripts/             # Helper scripts (generate API client, seed data, reset local DB)
├── .github/
│   └── workflows/       # CI/CD: lint + type-check + tests, build images, deploy, Android build
├── .env.example         # All environment variables with dummy values (never commit real secrets)
├── .editorconfig
├── .gitignore
└── README.md            # How to run everything locally, links to docs
```

| Folder | Purpose |
|---|---|
| `frontend/` | Everything the customer sees on web and Android. Talks to the backend only through the REST API. |
| `backend/` | Single Django project split into focused apps (catalog, orders, payments …). Also hosts the admin panel used by staff. |
| `infra/` | Reproducible environments: local services (PostgreSQL, Redis, MinIO, Mailpit, Meilisearch) and production containers. |
| `docs/` | Project documentation: `architecture/`, `prototype/` (HTML demos), setup and API conventions. |
| `scripts/` | One-off developer commands so nobody has to remember long CLI invocations. |
| `.github/workflows/` | Automated checks on every pull request and deployment pipelines. |

---

## 2. Frontend (`frontend/`)

Feature-based layout: every screen/section from the demo becomes a **feature** folder that owns its
components, hooks and state. Shared building blocks live outside `features/`.

```
frontend/
├── public/
│   ├── icons/                   # PWA icons, favicon, onlywheels-logo.svg
│   ├── models/                  # Small local 3D placeholders (real GLB files come from the CDN)
│   └── manifest.webmanifest     # Generated/extended by vite-plugin-pwa
├── src/
│   ├── main.tsx                 # Entry point: mounts <App/>, providers (Query, Router, i18n)
│   ├── app/
│   │   ├── App.tsx              # Root component
│   │   ├── router.tsx           # React Router 7 route tree
│   │   ├── providers.tsx        # QueryClientProvider, theme, i18n, auth context
│   │   └── layout/              # Page shell seen in the demo
│   │       ├── AnnouncementBar.tsx   # Top strip ("Un nou set. O nouă perspectivă…")
│   │       ├── Header.tsx            # Logo, desktop nav, garage/account/cart buttons + cart count
│   │       ├── MobileNav.tsx         # Bottom tab bar: Acasă, Catalog, Showroom, AI Studio, Coș
│   │       └── Footer.tsx
│   ├── routes/                  # Thin route files that compose features into pages
│   │   ├── index.tsx            # /            → Home
│   │   ├── catalog/             # /catalog, /catalog/$slug (product page)
│   │   ├── showroom.tsx         # /showroom
│   │   ├── ai-studio.tsx        # /ai-studio
│   │   ├── cart.tsx             # /cart
│   │   ├── checkout/            # /checkout, /checkout/success
│   │   ├── account/             # /account, /account/orders, /account/garage, /account/favorites
│   │   └── auth/                # /login, /register, /reset-password
│   ├── features/
│   │   ├── home/                # Hero, car stage, benefits row, category grid, brand strip,
│   │   │                        # featured products, Showroom/AI teasers, partner-fitting banner
│   │   ├── vehicle/             # Make → Model → Generation selector ("Totul începe cu mașina ta"),
│   │   │                        # "Garajul meu" (saved vehicles), active-vehicle store
│   │   ├── catalog/             # Product grid, product card, type tabs (Jante/Anvelope/Roți complete/
│   │   │                        # Accesorii), search box, filters (brand, size, PCD, ET, finish, price),
│   │   │                        # product detail page, fitment badge
│   │   ├── favorites/           # Heart toggle, favorites list (synced to backend when logged in)
│   │   ├── showroom3d/          # react-three-fiber scene: car + wheel GLB, finish/size switcher,
│   │   │                        # camera controls, "Add set of 4 to cart"
│   │   ├── ai-studio/           # Photo upload/camera, scene/angle/style picker, job status polling,
│   │   │                        # result gallery, quota display
│   │   ├── cart/                # Cart drawer/page, line items, sets of 4, fitting add-on, totals
│   │   ├── checkout/            # Address, delivery vs. garage fitting, slot picker, payment redirect
│   │   ├── fitting/             # Partner garages map/list, services, availability slots
│   │   ├── orders/              # Order history, order detail, tracking (AWB status)
│   │   ├── account/             # Profile, addresses, settings, language
│   │   └── auth/                # Login/register forms, Google/Apple login, token refresh logic
│   │       # Each feature folder typically contains:
│   │       #   components/  hooks/  store.ts (Zustand, if needed)  schemas.ts (Zod)  index.ts
│   ├── api/
│   │   ├── generated/           # AUTO-GENERATED by orval from Django OpenAPI – do not edit
│   │   ├── http.ts              # Fetch/axios instance: base URL, JWT header, refresh on 401
│   │   └── queryClient.ts       # TanStack Query defaults (stale times, retries)
│   ├── components/
│   │   ├── ui/                  # shadcn/ui primitives: Button, Dialog (modal), Select, Tabs, Toast …
│   │   ├── WheelVisual.tsx      # Reusable wheel illustration (silver/black/bronze finishes)
│   │   ├── Price.tsx            # RON formatting (Intl ro-RO)
│   │   └── Icon.tsx             # SVG sprite icons (car, cart, cube, spark, tool, pin …)
│   ├── lib/
│   │   ├── native/              # Platform adapters – Web API on browser, Capacitor plugin on Android
│   │   │   ├── camera.ts
│   │   │   ├── share.ts
│   │   │   ├── push.ts
│   │   │   └── storage.ts       # Token storage: httpOnly cookie (web) / Preferences (Android)
│   │   ├── analytics.ts         # PostHog wrapper
│   │   ├── sentry.ts            # Error tracking init
│   │   └── utils.ts             # cn(), formatters, small helpers
│   ├── stores/                  # Global Zustand stores shared across features (UI, toasts)
│   ├── i18n/
│   │   ├── index.ts             # i18next setup (ro default, en)
│   │   └── locales/
│   │       ├── ro/              # common.json, catalog.json, checkout.json …
│   │       └── en/
│   ├── styles/
│   │   └── globals.css          # Tailwind layers + design tokens (colors, fonts from the demo)
│   └── types/                   # Hand-written shared types not covered by the generated API
├── tests/
│   ├── unit/                    # Vitest + Testing Library (components, hooks, stores)
│   └── e2e/                     # Playwright (search → cart → checkout happy path)
├── android/                     # Generated by `npx cap add android` (phase 3) – native project
├── capacitor.config.ts          # App id, name, plugins, server URL for dev
├── orval.config.ts              # Points to backend /api/schema/ → writes src/api/generated
├── vite.config.ts               # React plugin, vite-plugin-pwa, path aliases
├── tailwind.config.ts
├── tsconfig.json
├── eslint.config.js
├── .env.example                 # VITE_API_URL, VITE_SENTRY_DSN, VITE_POSTHOG_KEY …
└── package.json                 # pnpm
```

### Mapping demo → frontend

| Demo element ([prototype/index.html](prototype/index.html)) | Frontend location |
|---|---|
| Announcement bar, header, footer, mobile bottom nav | `src/app/layout/` |
| Hero, benefits, category cards, brand strip | `src/features/home/` |
| Make / Model / Generation form, "Garajul meu" | `src/features/vehicle/` |
| Product tabs, search, product grid & cards | `src/features/catalog/` |
| Heart button on cards | `src/features/favorites/` |
| "Showroom 3D" section and modal | `src/features/showroom3d/` |
| "AI Photo Studio" section, local photo preview | `src/features/ai-studio/` + `src/lib/native/camera.ts` |
| Cart modal and cart count | `src/features/cart/` |
| "Montaj partener" banner | `src/features/fitting/` |
| Account button | `src/features/account/`, `src/features/auth/` |
| `<dialog>` modal, toast | `src/components/ui/` |
| Hard-coded `catalog` / `vehicles` arrays | Replaced by API calls via `src/api/generated/` |

---

## 3. Backend (`backend/`)

A Django **monolith** made of focused apps. Each app owns its models, API and admin; apps talk to each
other through `services.py` and signals, never by reaching into another app's internals.

```
backend/
├── config/
│   ├── settings/
│   │   ├── base.py              # Shared settings: installed apps, DRF, JWT, storages, Celery
│   │   ├── dev.py               # DEBUG, local MinIO/Mailpit, relaxed CORS
│   │   ├── prod.py              # Security headers, CSP, Sentry, S3/R2, WhiteNoise
│   │   └── test.py              # Fast password hasher, eager Celery, in-memory storage
│   ├── urls.py                  # /admin/, /api/v1/…, /api/schema/, /api/docs/ (Swagger)
│   ├── api_router.py            # Registers all DRF ViewSets under /api/v1/
│   ├── celery.py                # Celery app + Beat schedule
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── core/                    # Base models (UUID pk, timestamps), permissions, pagination,
│   │                            # exceptions, shared utils
│   ├── accounts/                # Custom User, profile, addresses, roles, auth endpoints (simplejwt cookies + Google ID token)
│   ├── vehicles/                # Makes, models, generations, user's saved vehicles ("Garajul meu")
│   ├── fitment/                 # FitmentSpec + compatibility engine (PCD, center bore, ET, diameter),
│   │                            # Wheel-Size API sync task
│   ├── catalog/                 # Brands, categories, products, variants, media, 3D models (GLB);
│   │                            # search (as built: catalog/filters.py + search_index.py, no search/ app)
│   ├── pricing/                 # Promotions, vouchers, old/new price rules
│   ├── inventory/               # Stock per variant, 30-min reservations, expiry task
│   ├── cart/                    # Cart & items, sets of 4, fitting add-on
│   ├── orders/                  # Checkout, order lifecycle & status history, VAT calculation
│   ├── payments/                # Stripe / Netopia sessions, webhooks, installments
│   ├── shipping/                # Sameday / Fan Courier AWB creation and tracking
│   ├── invoicing/               # SmartBill invoices + e-Factura (ANAF)
│   ├── garages/                 # Partner garages, services offered, opening hours, availability
│   ├── appointments/            # Fitting bookings linked to orders, garage confirmation
│   ├── ai_studio/               # AIGeneration jobs, gallery, quotas, cost tracking
│   │   └── providers/           # base.py (interface) + replicate.py, fal.py, openai.py, stability.py
│   ├── reviews/                 # Ratings & reviews, moderation, favorites
│   └── notifications/           # Email (anymail), push (FCM), in-app notifications, templates
├── templates/
│   ├── emails/                  # Order confirmation, shipping, appointment reminder …
│   └── admin/                   # django-unfold overrides
├── static/                      # Admin static assets (collected by WhiteNoise / S3)
├── tests/
│   ├── conftest.py              # pytest fixtures, factory_boy factories
│   ├── integration/             # Cross-app flows (checkout → payment webhook → invoice/AWB)
│   └── fixtures/                # Demo data (vehicles, products) – same as the prototype
├── manage.py
├── pyproject.toml               # uv dependencies + ruff, mypy, pytest config
├── uv.lock
└── .env.example                 # DATABASE_URL, REDIS_URL, S3_*, STRIPE_*, AI provider keys …
```

### Inside a Django app (example: `apps/catalog/`)

```
catalog/
├── migrations/          # Auto-generated database schema changes
├── models.py            # Product, ProductVariant, ProductMedia, Model3D, Brand, Category
├── serializers.py       # DRF serializers (JSON in/out)
├── views.py             # DRF ViewSets (list, retrieve, filters)
├── urls.py              # Router registration for this app
├── filters.py           # django-filter FilterSets (brand, size, PCD, finish, price)
├── services.py          # Business logic – the only entry point other apps may call
├── selectors.py         # Read-only query helpers (optimized querysets)
├── tasks.py             # Celery tasks (e.g. thumbnail generation, search reindex)
├── signals.py           # Reactions to events (e.g. product saved → reindex)
├── admin.py             # Django Admin config (+ import/export, history)
├── apps.py
└── tests/               # test_models.py, test_api.py, test_services.py
```

---

## 4. Infrastructure (`infra/`)

```
infra/
├── docker-compose.yml           # Local: postgres, redis, minio, mailpit, (meilisearch)
├── docker-compose.prod.yml      # Prod-like stack: web, worker, beat, nginx
├── docker/
│   ├── backend.Dockerfile       # One image → run as web (Gunicorn/Uvicorn), worker or beat
│   └── frontend.Dockerfile      # Optional: static build served by Nginx (if not on Cloudflare Pages)
├── nginx/
│   └── default.conf             # Reverse proxy, TLS, gzip/brotli, caching for static files
└── monitoring/                  # Flower, Grafana/Loki config, uptime checks
```

| Service | Role |
|---|---|
| `postgres` | Main database (source of truth) |
| `redis` | Cache, Celery broker, rate limiting |
| `minio` | Local S3 replacement for images, GLB models, AI results, invoices |
| `mailpit` | Catches outgoing emails locally |
| `meilisearch` | Catalog search (phase 4) |

---

## 5. Documentation (`docs/`)

```
docs/
├── architecture/
│   ├── ARCHITECTURE.md          # System architecture (+ §13 as-built status and changed decisions)
│   └── ARCHITECTURE.html
├── prototype/
│   ├── index.html               # Homepage concept (static HTML)
│   └── app_concept.html
├── api/CONVENTIONS.md           # API conventions, endpoints, error format
├── SETUP.md                     # Development setup on a new machine
├── DEPLOYMENT.md                # Production plan (own domain)
├── ROADMAP.md                   # First-run checklist, known limitations, next steps, task split
└── PROJECT_STRUCTURE.md         # This file
```

---

## 6. CI/CD (`.github/workflows/`)

| Workflow | What it does |
|---|---|
| `backend.yml` | `ruff` + `mypy` + `pytest` (with PostgreSQL & Redis services), checks for missing migrations |
| `frontend.yml` | `eslint` + `tsc` + `vitest`, verifies the generated API client is up to date |
| `e2e.yml` | Playwright tests against a full Docker Compose stack |
| `deploy.yml` | Build images → run `migrate` → deploy to staging, then production (manual approval) |
| `android.yml` | `npx cap sync` + Gradle build → Play Console internal track (phase 3) |

---

## 7. Scripts (`scripts/`)

| Script | Purpose |
|---|---|
| `generate-api-client` | Export OpenAPI schema from Django and run orval |
| `seed-demo-data` | Load the prototype's vehicles and products into the local DB |
| `reset-db` | Drop, recreate and migrate the local database |
| `dev` | Start Docker services + Django + Celery + Vite together |
