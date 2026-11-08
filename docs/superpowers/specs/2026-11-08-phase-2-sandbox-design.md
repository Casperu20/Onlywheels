# Phase 2 sandbox integrations and experiences

## Intent

Turn the existing Phase 2 scaffolding into demonstrable, end-to-end sandbox features for the OnlyWheels university project, while keeping provider boundaries, configuration, and operational behavior suitable for a later real website. Do not treat credentials as a substitute for implementing or testing the provider workflows.

## Goals

- Implement Netopia sandbox checkout and a verified, idempotent payment webhook; retain the existing Stripe and development fake-provider behavior.
- Issue an invoice through SmartBill's available test environment after successful payment, persist the provider identifiers and PDF, and expose invoice state to staff and the customer.
- Create and track courier shipments through Sameday and Fan Courier adapters, with an explicit configured carrier and controlled retries.
- Implement AI image generation through the existing provider interface, authenticated API endpoints, queued status, quota enforcement, user-owned results, and a frontend flow.
- Replace the 3D showroom placeholder with a usable wheel viewer/configurator driven by the existing product `Model3D` data.
- Keep secrets in environment configuration, make sandbox/live selection explicit, and document account setup, local operation, limitations, and the later production switch.

## Non-goals

- Accepting live payments, issuing legally relied-upon invoices, or creating production shipping labels during this work.
- Legal/accounting certification of Romanian VAT, e-Factura, consumer, privacy, retention, or carrier rules.
- A vehicle-on-road 3D configurator in the absence of licensed car GLB assets. The first showroom is wheel-first; car models can be added later without changing the product-model contract.
- Android app release, push notifications, automatic production deployment, or a full garage portal.
- Silently falling back to fake provider behavior when a real adapter is misconfigured or a provider request fails.

## Approaches considered

1. **Integrated slices (selected):** finish each feature through the user interface/API, provider adapter, configuration, and automated tests, wiring payment into the order workflows. This gives testable end-to-end paths and reveals integration issues at their boundaries.
2. **Backend first:** implement all providers and persistence before the customer-facing 3D and AI work. This prioritizes service plumbing, but leaves the user-visible demo incomplete for longer.
3. **Mock-only implementation:** build local simulations and defer provider calls. This is quicker, but does not meet the request for real provider adapters and sandbox testing.

## Existing state and constraints

- Payment selection currently supports `fake` and `stripe`. `Payment` and `WebhookEvent` already provide attempt state and webhook idempotency; `mark_paid` is the canonical paid-order transition.
- `Invoice`, `Shipment`, and `AIGeneration` models and admin pages exist. Invoice/courier services and Netopia, carrier, and AI provider implementations are stubs.
- Order status changes happen in `apps/orders/services.py`; payment and staff transitions are suitable integration points for background work.
- Celery and storage configuration exist. Development tasks run eagerly by default; production compose provides Redis and workers.
- The frontend has a wheel product's `model_3d` API field, but no 3D assets or 3D rendering dependencies. The showroom route is a placeholder.
- There are no initial backend migrations or backend lockfile in the current workspace, so database-backed validation requires preparing the documented first-run environment.
- Provider sandbox availability and access vary. Code can be implemented without secrets, but exercising real sandbox requests requires the user to configure provider-issued credentials locally. Secrets must not be sent in chat or committed.

## Proposed implementation

### 1. Netopia sandbox payments

- Add a real Netopia adapter behind the existing `PaymentProvider` interface and register it alongside Stripe and fake.
- Keep provider selection explicit in Django settings and `.env.example`; use distinct sandbox/live configuration and refuse ambiguous or incomplete configuration.
- Start the provider checkout from the existing order flow, persist the provider transaction/session reference, and redirect to the hosted payment page.
- Add a Netopia webhook endpoint that validates the provider's documented signature/authentication, validates order/amount/currency against the stored payment, records events idempotently, and calls the existing paid-order transition exactly once.
- Handle success, failure, cancellation, and duplicate/out-of-order callbacks. Do not mark an order paid based on the browser redirect.
- Preserve `fake` for local tests and Stripe unchanged.

### 2. SmartBill invoices

- Implement a SmartBill adapter/service using documented API requests and explicit sandbox credentials/configuration.
- Schedule invoice creation only after the canonical paid transition commits. Make creation idempotent and safe to retry; surface provider errors without falsely marking the invoice successful.
- Persist invoice series/number/date/total, PDF, and e-Factura state in the existing model; add status refresh/retry support only for provider operations supported by its API.
- Expose a customer's own invoice through an authenticated order detail/download path; retain staff visibility in Django Admin.
- Keep company profile/CIF and invoice series as server-side configuration. Use the existing order contact/address snapshot unless the provider's sandbox contract requires additional checkout fields; any new customer billing fields must be explicit, validated, and snapshotted on the order.

### 3. Courier shipments

- Implement both existing carrier adapters against their documented sandbox APIs, with carrier selection explicit in configuration or staff workflow.
- Create an AWB when staff moves an eligible courier order to processing; do not create a courier shipment for garage-fitting orders.
- Persist carrier, AWB, tracking URL, label, parcel count, weight, and normalized status. Retry transient provider failures safely; do not advance an order to shipped until an AWB succeeds.
- Add a periodic tracking task and ensure terminal statuses do not regress. Preserve current manual status actions when no live carrier is configured.
- The existing catalog has no shipping weight/dimension fields. Add a validated per-variant weight and seed demo values (or another approved source) before computing shipment weight; require staff configuration for sender/return addresses.

### 4. AI photo studio

- Implement real adapters for the already-present Replicate and fal provider interfaces, selected explicitly by `AI_STUDIO_PROVIDER`; validate each provider's request format, response parsing, timeouts, and cost/result handling.
- Add authenticated create/status/list endpoints. Accept bounded, validated uploads; verify content type and image dimensions; enforce per-user quota and ownership; never expose another user's input or result.
- Retain the existing default quota of five generations per user per day and add a configurable whole-account estimated provider-spend ceiling of USD 5/day. Reject new jobs when the ceiling would be exceeded; record provider-reported cost and document that estimates do not guarantee the provider's final bill.
- Queue work through Celery, preserve queued/running/done/failed states, and make provider errors visible to the user without leaking keys or sensitive provider responses.
- Store AI input/output in private storage separate from public product media: a non-served local directory in development and a private S3-compatible bucket in deployment. Serve images only through owner-authorized endpoints; upload input bytes to each AI provider through its documented file-upload mechanism rather than exposing public media URLs. Do not require direct-to-bucket customer uploads for the first working version.
- Delete uploaded input and result images after 30 days, and allow the owner to delete them earlier.
- Build the frontend workflow for selecting a product/variant, uploading a photo, selecting supported scene/style options, viewing progress/results, and retrying an eligible failure. Use a generated 3D render only after the showroom provides one.
- Avoid promising precise wheel replacement in arbitrary photos: image-to-image generation is an illustrative result and must be labeled as such.

### 5. Wheel-first 3D showroom

- Replace the showroom placeholder with a lazy-loaded React Three Fiber view using the product's `model_3d` GLB and accessible loading/error/no-model states.
- Support basic camera controls, loading progress, a sensible mobile fallback, and product/variant selection where model data exists.
- Keep rendering dependencies out of the initial route bundle. Add only the libraries required for the viewer.
- No wheel GLB is currently present. The viewer must explain that an admin needs to upload a licensed product GLB when one is unavailable. Use no unlicensed third-party model assets.
- A car GLB and fitment-to-car-model mapping are explicitly deferred until the user supplies licensed assets.

## Shared configuration and operations

- Add documented, empty environment variables for provider mode, sandbox/live base URLs, account identifiers, API credentials, webhook secrets, company/sender profile, Celery, and AI provider settings as applicable.
- Never store secrets in frontend build variables, database fixtures, tests, or documentation examples.
- For enabled integrations, fail visibly at startup or on the attempted operation when required settings are missing; do not silently substitute the fake provider.
- Provide example local commands for migrations, Redis/worker startup when needed, and provider sandbox webhooks. Keep test settings deterministic and mock external HTTP calls in automated tests.
- Update setup, deployment, and roadmap docs to distinguish implemented code, credential-dependent sandbox verification, and production/legal prerequisites.

## Delivery order

1. Implement and test Netopia checkout/webhook while preserving Stripe/fake tests.
2. Wire paid orders to idempotent SmartBill invoice creation; test retry and customer/staff access.
3. Implement and test carrier shipment creation/tracking from eligible order transitions.
4. Implement AI provider adapters, API, worker flow, quota/ownership behavior, and frontend studio.
5. Implement the wheel-first 3D viewer and its asset-missing/mobile behavior.
6. Document provider setup and run the complete backend/frontend test and build checks; run real provider sandbox journeys once the user has locally configured credentials.

This order puts payment before its downstream invoice and fulfillment workflows. AI and 3D remain independently testable slices.

## Acceptance criteria

- Provider selection and sandbox/live configuration are explicit. Existing fake and Stripe payment flows remain covered by tests.
- Netopia webhook authenticity, amount/currency matching, duplicate delivery, and order idempotency are tested; the browser return alone cannot mark an order paid.
- A paid order can create exactly one SmartBill invoice; failure and retry are observable; its PDF/status is accessible only to the order owner and staff.
- A courier order can create and track one shipment through either configured carrier adapter; garage fitting does not trigger an AWB; provider failure does not falsely mark an order shipped.
- AI endpoints enforce authentication, ownership, upload limits, quotas, state transitions, and error reporting; mocked-provider tests cover success/failure, and the UI presents the full job flow.
- AI usage enforces five generations per user per day and the configurable estimated USD 5 account-wide daily provider-spend ceiling; uploads and results expire after 30 days, and owners can delete them sooner.
- AI input/result objects are not reachable from the public media path or public bucket; user access is owner-authorized, and provider input transfer uses documented upload APIs.
- A product with a licensed uploaded GLB renders in the wheel viewer; missing model and unsupported rendering states are handled without breaking product browsing.
- Automated tests mock external providers and pass in CI. A separately documented manual sandbox checklist records which real providers still require credentials/accounts for verification.
- No secret is added to the repository; the development fake-payment behavior is not available in production settings.

## Decisions left to the implementer

- Exact provider API versions, sandbox URLs, signature formats, and response schemas must be verified against current official provider documentation before writing adapters.
- Add only the required fields and dependencies once the provider contracts establish their need.
- A real sandbox run cannot be claimed until provider-issued credentials are configured locally and the callback/webhook path is reachable.
- Production launch still requires legal/accounting review, privacy and retention decisions, real catalog/model assets, live credentials, HTTPS, and operational backup/monitoring checks.
