# Android App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an installable Capacitor Android app with native email/password sessions, customer account/cart/checkout flows, and a return from simulated payment.

**Architecture:** Keep the existing React/Vite app as the UI and package it with Capacitor Android. Add distinct native JWT endpoints while preserving the browser cookie/CSRF flow; the Android client stores tokens in secure storage and uses bearer auth. Register a custom Android deep link for the simulated checkout return and confirm the resulting order state through the existing API.

**Tech Stack:** React 19, Vite, Capacitor 8, Android Gradle, Django REST Framework, SimpleJWT, pytest, Vitest, pnpm, uv.

**Spec:** [2026-11-15-android-app-design.md](../specs/2026-11-15-android-app-design.md)

## Global Constraints

- Package the current React/Vite app with Capacitor; do not rewrite its UI in native Android.
- The app must use a backend URL reachable from the Android device; never assume `localhost` refers to the developer's computer from Android.
- Store native access/refresh tokens using platform-secure storage; do not write tokens to localStorage or the Preferences-backed non-sensitive storage adapter.
- Preserve the existing browser cookie/CSRF authentication behavior.
- Existing JWT policy is 15-minute access tokens and 7-day refresh tokens, with refresh rotation and blacklist-after-rotation enabled.
- The existing Capacitor Android scheme remains HTTPS and mixed content remains disabled.
- Verify checkout with the simulated payment flow and confirm order/payment state through the backend.
- Push/FCM, Play Store release, production signing, native Google sign-in, live payments, and a native UI rewrite are out of scope.

## Review Focus

- Invalid, expired, or replayed native refresh tokens must fail and clear the client session; pin this in backend auth tests and the frontend refresh-interceptor tests.
- Native login/registration must return tokens without changing cookie-based browser responses; pin both response contracts in backend auth tests.
- Browser unsafe requests must still require CSRF while native bearer requests do not depend on cookies; keep and rerun the existing CSRF tests and cover the native request path in frontend tests.
- A missing or misconfigured device API URL must not silently target localhost; document the reachable `VITE_API_URL` setup and verify API calls from the device.
- A forged or stale payment deep link must not mark an order paid; test that the app fetches authoritative order state and that only the authenticated simulated-payment API changes payment state.

---

### Task 1: Create the Capacitor Android project

**Files:**
- Modify: `frontend/package.json` and the generated `frontend/pnpm-lock.yaml`
- Modify: `frontend/capacitor.config.json`
- Modify: `frontend/.env.example`
- Modify: `backend/.env.example` to allow the Capacitor origin
- Create: `frontend/scripts/check-android-env.mjs`
- Create: `frontend/tests/unit/android-config.test.ts`
- Create: `frontend/android/` using Capacitor CLI; retain the generated Android project in the source tree
- Modify: `docs/SETUP.md` with Android prerequisites, device API URL setup, and debug build/install commands

**Interfaces:**
- Consumes: Existing Vite production output in `frontend/dist` and Capacitor config (`appId: ro.onlywheels.app`, `webDir: dist`).
- Produces: Capacitor 8 Android project and repeatable `pnpm android:sync`, `pnpm android:run`, and `pnpm android:build` scripts to validate device API configuration, build the web app, sync native assets, and run/build Android.
- Produces: `validateAndroidApiUrl(value: string | undefined): URL`, which returns a valid non-loopback HTTPS URL or throws an explicit configuration error.

- [x] **Step 1: Write Android API URL validation tests**

Add `test_accepts_reachable_https_api_url`, `test_rejects_missing_api_url`, `test_rejects_malformed_api_url`, and `test_rejects_loopback_api_url` (`localhost`, `127.0.0.1`, `::1`).

- [x] **Step 2: Run the focused tests and confirm they fail**

Run from `frontend`: `pnpm exec vitest run tests/unit/android-config.test.ts`.
Expected: tests fail because URL validation has not been implemented.

- [x] **Step 3: Add Capacitor dependencies and platform scripts**

Add matching Capacitor 8 `@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/app`, and `@capacitor/app-launcher` packages, plus `@aparajita/capacitor-secure-storage` 8.x. Define `android:sync` as preflight + web build + Capacitor sync, `android:run` as sync + `cap run android`, and `android:build` as sync + Gradle `assembleDebug`.

- [x] **Step 4: Implement Android API URL preflight**

Implement `frontend/scripts/check-android-env.mjs` to load the production Vite environment, validate that `VITE_API_URL` is an absolute HTTPS URL with a non-loopback hostname, and fail explicitly otherwise. Run this preflight before Android build/sync.

- [x] **Step 5: Generate and configure Android**

Run `pnpm exec cap add android`, preserve HTTPS and `allowMixedContent: false`, and verify generated Android configuration uses `ro.onlywheels.app` and embeds `dist`.

- [x] **Step 6: Document device setup**

Update the frontend environment example and `docs/SETUP.md` to explain that `VITE_API_URL` must be a backend URL reachable by the device, with no development host hard-coded into committed files. Add `https://localhost` to the backend's explicit CORS allowed-origin example while retaining the existing frontend origin; do not broaden CORS to all origins. Document Android Studio/JDK/SDK prerequisites and the debug install command.

- [ ] **Step 7: Verify the Android shell on a device**

Run: the Android URL-validation tests, `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build`, then `pnpm android:sync` and `pnpm exec cap run android` with the available emulator/device.
Expected: existing web checks pass, Capacitor sync succeeds, and OnlyWheels launches from the Android app icon with public catalog access.

### Task 2: Add native JWT authentication endpoints

**Files:**
- Modify: `backend/apps/accounts/views.py`
- Modify: `backend/apps/accounts/urls/auth.py`
- Modify: `backend/apps/accounts/tests/test_auth.py`

**Interfaces:**
- Consumes: Existing `LoginSerializer`, `RegisterSerializer`, `UserSerializer`, SimpleJWT settings, and bearer `CookieJWTAuthentication`.
- Produces:
  - `POST /api/v1/auth/native/login/` and `/native/register/`: existing credentials payload; response `{ "user": User, "access": string, "refresh": string }`.
  - `POST /api/v1/auth/native/refresh/`: `{ "refresh": string }` → `{ "access": string, "refresh": string }`, rotating and blacklisting the old refresh token.
  - `POST /api/v1/auth/native/logout/`: `{ "refresh": string }` → 204 after blacklist.
  - Native public auth requests remain rate-limited; they do not require cookie CSRF. Existing web endpoints and response bodies remain unchanged.

- [x] **Step 1: Write native auth contract tests**

Add tests named `test_native_login_returns_user_and_token_pair`, `test_native_register_returns_token_pair_and_creates_session`, `test_native_refresh_rotates_and_rejects_reuse`, `test_native_logout_blacklists_refresh`, and `test_native_auth_does_not_change_cookie_login_contract`. Assert token validity, correct status/body, immediate session after registration, old-refresh rejection, and unchanged httpOnly browser cookies.

- [x] **Step 2: Run the targeted tests and confirm they fail**

Run from `backend`: `uv run pytest apps/accounts/tests/test_auth.py -q`.
Expected: native route tests fail because endpoints do not exist; existing auth tests remain green.

- [x] **Step 3: Implement native auth views and routes**

Add the four `/native/` routes using existing serializers and shared account/authentication logic. Return JWTs only from these native routes, apply existing token lifetime/rotation/blacklist settings, retain the auth rate limit, and leave web cookie/CSRF views unchanged.

- [x] **Step 4: Run backend auth and schema checks**

Run from `backend`: `uv run pytest apps/accounts/tests/test_auth.py -q`, then `uv run python manage.py spectacular --validate --file "$env:TEMP\onlywheels-openapi.yml"`.
Expected: auth tests pass, schema validation succeeds, and existing browser CSRF tests still pass.

### Task 3: Implement secure native sessions in the frontend

**Files:**
- Create: `frontend/src/lib/native/auth-storage.ts`
- Modify: `frontend/src/lib/native/index.ts`
- Modify: `frontend/src/api/http.ts`
- Modify: `frontend/src/features/auth/api.ts`
- Create: `frontend/tests/unit/native-auth.test.ts`

**Interfaces:**
- Consumes: Task 2 native auth endpoint contracts and the Capacitor secure-storage package from Task 1.
- Produces:
  - `AuthTokens = { access: string; refresh: string }`
  - `getNativeTokens(): Promise<AuthTokens | null>`
  - `setNativeTokens(tokens: AuthTokens): Promise<void>`
  - `clearNativeTokens(): Promise<void>`
  - Native login/register resolve to the existing `User` shape after storing tokens; web login/register continue resolving to `User` using cookies.

- [x] **Step 1: Write frontend session tests**

Add tests proving native requests attach `Authorization: Bearer <access>`, omit cookie/CSRF behavior, coalesce concurrent 401 refreshes, persist rotated tokens, retry a request once, clear tokens after refresh failure and in a logout `finally` path, and preserve the browser cookie/CSRF path.

- [x] **Step 2: Run focused frontend tests and confirm they fail**

Run from `frontend`: `pnpm exec vitest run tests/unit/native-auth.test.ts`.
Expected: tests fail because the native token adapter and request behavior are not implemented.

- [x] **Step 3: Implement the secure-storage adapter**

Implement the three async token functions over `@aparajita/capacitor-secure-storage`. Do not fall back to localStorage or Preferences on Android; surface secure-storage failures rather than reporting a successful login without durable secure credentials.

- [x] **Step 4: Add native request and session handling**

Update `http.ts` to detect Capacitor native mode, attach the stored bearer access token, disable cookie/CSRF behavior for native API calls, and refresh via the native endpoint with one shared in-flight refresh promise. Clear native credentials after refresh failure. Update `authApi` so native login/register store returned tokens and return `user`, and native logout attempts to blacklist the stored refresh token and always clears local credentials in `finally`, while surfacing API failures. Keep web behavior unchanged.

- [x] **Step 5: Run frontend validation**

Run from `frontend`: `pnpm exec vitest run tests/unit/native-auth.test.ts tests/unit/auth-schemas.test.ts`, `pnpm typecheck`, and `pnpm lint`.
Expected: focused tests, typecheck, and lint pass.

### Task 4: Handle simulated checkout return through an Android deep link

**Files:**
- Create: `frontend/src/lib/native/deep-links.ts`
- Create: `frontend/tests/unit/native-deep-links.test.ts`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/routes/CheckoutPage.tsx`
- Modify: `frontend/src/routes/OrderPages.tsx`
- Modify: `frontend/android/app/src/main/AndroidManifest.xml`

**Interfaces:**
- Consumes: Capacitor App and App Launcher plugins, Task 1 Android project, and Task 3 bearer-authenticated order APIs.
- Produces: parser/handler for `onlywheels://checkout/success?order=<number>` that navigates to the existing `/checkout/success?order=<number>` route for both cold and warm app starts.

- [x] **Step 1: Write deep-link and payment-flow tests**

Test valid custom-scheme success links, reject unrelated schemes/hosts/paths or missing order numbers, and verify a valid return displays the backend order state rather than treating link parameters as proof of payment. Cover native-only routing to the bundled fake-payment page; preserve the browser redirect behavior.

- [x] **Step 2: Run the focused tests and confirm they fail**

Run from `frontend`: `pnpm exec vitest run tests/unit/native-deep-links.test.ts`.
Expected: tests fail because the deep-link handler and native checkout behavior are not implemented.

- [x] **Step 3: Register Android deep links and app listeners**

Add the `onlywheels://checkout/success` intent filter to the Android manifest. In `deep-links.ts`, accept only the configured scheme, host, and route, require an order number, and route to the existing success page. Register the listener in `main.tsx` and process both `App.getLaunchUrl()` and `appUrlOpen` events.

- [x] **Step 4: Complete simulated checkout in the app**

In native mode, keep the existing `/checkout/fake-pay` flow inside the bundled app rather than navigating to the remote frontend URL. After the authenticated fake-complete API succeeds, open the configured success deep link with `AppLauncher.openUrl` so Android resumes/routes the app. Do not mark an order paid from a URL parameter; continue fetching order state from the API.

- [x] **Step 5: Run frontend checks**

Run from `frontend`: `pnpm test`, `pnpm typecheck`, `pnpm lint`, and `pnpm build`.
All four frontend checks pass. Android sync/run remain pending the device API URL and Android SDK setup.

- [ ] **Step 6: Verify device acceptance**

Run `pnpm exec cap sync android` and `pnpm exec cap run android`.
On an available device/emulator and reachable test backend, verify registration/login, profile, order history, cart,
simulated payment, cold/warm deep-link return, and order status refresh. Verify invalid deep links do not navigate
into payment success.

### Task 5: Final cross-platform regression

**Files:**
- No new files; update `docs/SETUP.md` or `docs/ROADMAP.md` if actual Android status/build steps differ from earlier task instructions.

**Interfaces:**
- Consumes: Completed Tasks 1–4.
- Produces: Verified Android debug build and unchanged browser auth/checkout behavior.

- [x] **Step 1: Run complete targeted project checks**

Run from `backend`: `uv run pytest apps/accounts/tests/test_auth.py apps/payments/tests/test_payments.py -q`.
Run from `frontend`: `pnpm test`, `pnpm typecheck`, `pnpm lint`, and `pnpm build`.
Expected: all selected tests and checks pass.

- [ ] **Step 2: Rebuild and install the debug app**

Run `pnpm android:build` and `pnpm android:run` with the reachable test backend URL configured.
Expected: app installs and launches on the available device/emulator without mixed-content or API-origin workarounds.
