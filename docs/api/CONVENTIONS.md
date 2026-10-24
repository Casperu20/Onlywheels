# API conventions

Agreed between frontend and backend. Every new endpoint follows these rules.

## URLs

- Base path: `/api/v1/`. A breaking change means `/api/v2/`, never silent changes.
- Plural, lowercase, kebab-case resources: `/api/v1/catalog/products/`, `/api/v1/accounts/addresses/{id}/`.
- Always a trailing slash.
- Field names in JSON are `snake_case` (the generated TypeScript types keep them as-is).

## Authentication

| Client | How |
|---|---|
| Web (React) | httpOnly cookies `ow_access` (15 min) + `ow_refresh` (7 days, rotated). JavaScript never sees the tokens. |
| Android / other | `Authorization: Bearer <access>` header. |

- Every unsafe request (`POST`, `PUT`, `PATCH`, `DELETE`) from the web sends the `X-CSRFToken` header
  (value of the `csrftoken` cookie, obtained from `GET /api/v1/csrf/`). The axios client does this automatically.
- On `401`, the client calls `POST /api/v1/auth/refresh/` once and retries the request.
- Endpoints are **private by default**; public ones explicitly use `AllowAny`.

Auth endpoints (`/api/v1/auth/`): `register/`, `login/`, `google/`, `refresh/`, `logout/`, `me/`,
`password/change/`, `password/reset/`, `password/reset/confirm/`, and GDPR: `me/export/` (GET, JSON with all
personal data) and `me/delete/` (POST `{"password"}`, or `{"confirm_email"}` for Google-only accounts –
`has_password` in `me/` tells which; anonymises the user, keeps orders, clears the cookies, `204`).

## Main endpoints

| Area | Endpoints |
|---|---|
| Vehicles (public) | `GET vehicles/makes/`, `GET vehicles/models/?make=<id>`, `GET vehicles/generations/?model=<id>`, `GET vehicles/generations/<id>/` (includes `fitment`) |
| My garage (auth) | `GET/POST vehicles/my/`, `PATCH/DELETE vehicles/my/<id>/` |
| Catalog (public) | `GET catalog/brands/`, `GET catalog/categories/`, `GET catalog/products/`, `GET catalog/products/<slug>/?vehicle=<generation id>` |
| Favorites (auth) | `GET favorites/`, `PUT/DELETE favorites/<product id>/` |
| Reviews | `GET reviews/?product=<slug>` (public, approved only), `POST reviews/`, `GET reviews/mine/?product=<slug>` |
| Cart (auth) | `GET/DELETE cart/`, `POST cart/items/`, `PATCH/DELETE cart/items/<id>/`, `POST cart/merge/` (guest cart after login) |
| Garages (public) | `GET garages/`, `GET garages/<slug>/`, `GET garages/<slug>/slots/?date=YYYY-MM-DD` |
| Checkout (auth) | `POST checkout/preview/` (totals), `POST orders/` (place order) |
| Orders (auth) | `GET orders/`, `GET orders/<number>/`, `POST orders/<number>/pay/` → `{checkout_url}`, `POST orders/<number>/cancel/` |
| Payments | `POST payments/webhook/stripe/` (Stripe only, signed), `POST payments/fake/complete/` (dev only) |

Business errors: `out_of_stock` (409) when stock changed since the cart was filled;
voucher and slot problems are `validation_error` on `voucher_code` / `slot_start`.

`GET catalog/products/` filters: `type`, `brand` (slugs, comma separated), `category`, `featured`, `search`,
`diameter` (comma separated), `finish`, `season`, `tire_size`, `pcd`, `price_min`, `price_max`, `in_stock`,
`vehicle` (generation id → only products that fit), `ordering` (`price`, `-price`, `name`, `-newest`, `-rating`).
All variant-level filters apply to the **same variant**; `min_price` and `cheapest_variant` describe the cheapest matching variant.

## Errors

Every error response has the same shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "First human-readable message",
    "fields": { "email": ["An account with this email already exists."] }
  }
}
```

- `fields` is present only for `validation_error` (HTTP 400).
- Other codes: `not_authenticated` / `token_not_valid` (401), `permission_denied` (403), `not_found` (404),
  `throttled` (429). New business errors get their own `code` (e.g. `out_of_stock`, `voucher_expired`).
- Messages follow the `Accept-Language` header (`ro` or `en`); the frontend sends the current UI language.

## Status codes

| Action | Code |
|---|---|
| Read / update | `200` |
| Create | `201` + created object |
| Action without body (logout, delete) | `204` |
| Async job accepted (AI generation) | `202` + `{ "id": ... }` |

## Pagination, filtering, ordering

List endpoints are paginated:

```json
{ "count": 120, "next": "…?page=2", "previous": null, "results": [ … ] }
```

- `?page=2&page_size=24` (max 100).
- Filters as query params: `?brand=bbs&diameter=18&finish=black&price_min=500&price_max=2000`.
- Ordering: `?ordering=price` / `?ordering=-price`.
- Search: `?search=ultraleggera`.

## Data types

| Type | Format |
|---|---|
| IDs | UUID strings |
| Money | decimal **string** in RON, 2 decimals: `"1890.00"` (never floats) |
| Dates / times | ISO 8601 with timezone: `"2026-10-24T14:30:00+03:00"` |
| Enums | lowercase strings: `"pending_payment"`, `"wheel"` |
| Images / files | absolute URLs |

## OpenAPI

- Schema: `/api/schema/`, docs: `/api/docs/`.
- Every view has `@extend_schema(tags=[...])` and explicit request/response serializers
  so the generated client has proper types.
- After changing the API, the backend developer runs `pnpm api:generate` (or asks the frontend developer to) and commits the result.
