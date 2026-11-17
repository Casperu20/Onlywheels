# Android app with signed-in flows

**Status:** Draft for approval

## Intent

Get the existing OnlyWheels React application running as an installable Android app. The first milestone should make the app useful while signed in, rather than stopping at an app icon and public pages. Notifications are explicitly out of scope until there is a clear product use case.

## Goals

- Package the current React/Vite app with Capacitor; do not rewrite its UI in native Android.
- Create and build the Android project, with a debug APK installable on an Android emulator or phone.
- Keep the API URL configurable and point the app to a backend reachable from the device; never assume `localhost` refers to the developer's computer from Android.
- Support native email/password login and registration, authenticated account requests, cart, and the existing checkout flow.
- Store native access/refresh tokens using platform-secure storage, attach bearer access tokens to API calls, and refresh or clear sessions safely.
- Preserve the existing browser cookie/CSRF authentication behavior.
- Return to the app after the existing simulated payment flow using a configured deep link; confirm payment state with the backend rather than trusting link parameters.
- Verify the Android build and exercise signed-in flows against a non-production backend and simulated payment.

## Non-goals

- Push notifications or FCM registration/delivery.
- Play Store release, production signing, or publishing.
- Rewriting screens in Kotlin/Java or changing the existing web/PWA experience.
- Native Google sign-in, unless required by the implementation review; email/password is the initial native sign-in path.
- Converting camera and share adapters to native plugins; existing web fallbacks remain for this milestone.
- Real payment-provider credentials or live transactions; checkout validation uses the simulated payment flow.

## Current constraints

- The frontend has a Capacitor config and adapter placeholders, but no Capacitor dependencies or Android project.
- The frontend HTTP client currently relies on cookies and CSRF. Login/register return the user and set httpOnly cookies; they do not return a token payload for native storage.
- The backend JWT authentication class accepts bearer credentials, so the existing browser flow can remain intact while native auth is added.
- Existing JWT policy is 15-minute access tokens and 7-day refresh tokens, with refresh rotation and blacklist-after-rotation enabled. Registration signs the new user in immediately.
- `VITE_API_URL` configures API access. A physical phone/emulator needs a reachable backend URL; the local Vite proxy and `127.0.0.1` are not suitable for a device build.
- Native tokens must not be written to localStorage or the existing Preferences-backed non-sensitive storage adapter.
- The existing Capacitor Android scheme remains HTTPS and mixed content remains disabled.

## Approaches considered

1. **Capacitor wrapper (chosen):** reuse the React app, add Capacitor Android support, and bridge native authentication through secure token storage. This fits the existing codebase and produces a phone-installable app without maintaining a second UI.
2. **Native Android rewrite:** rebuild product screens and flows in Android-specific UI. This adds a second frontend and is disproportionate to the immediate goal.
3. **PWA only:** install the existing web app from the browser. It is the lightest option, but does not produce the native Android app requested.

## Design and behavior

- Capacitor wraps the built web app; Vite build output is synchronized into the Android project using the standard Capacitor workflow.
- Add native email/password login and registration responses that provide JWT credentials, plus native refresh/logout handling. Persist credentials in Android secure storage, send the access token as a bearer token, follow the existing token lifetime/rotation policy, and revoke/clear credentials on logout. The web client continues using httpOnly cookies and CSRF as it does today.
- The signed-in scope covers customer profile access, order history, cart, and checkout; account deletion/GDPR actions and Google sign-in remain deferred.
- Configure a payment return link for the simulated checkout. On return, let the app resume the order flow and fetch authoritative payment/order status from the API.
- Add only the Capacitor native dependencies needed for the shell and secure credential storage. Keep the existing browser behavior for non-auth native adapters.
- Configure the API endpoint at build time using the existing `VITE_API_URL` mechanism. Do not hard-code a development or production host into the app.
- The initial delivery is a locally buildable/debug-installable app, not a Play Store release.

## Acceptance checks

- Frontend typecheck, lint, tests, and production build pass.
- Backend auth tests cover native token issuance/refresh/logout without regressing the cookie-based browser flow.
- Checkout's simulated payment returns to the installed app, which then verifies the order/payment status through the backend.
- Capacitor sync and Android debug build succeed with the documented local Android SDK setup.
- On the available Android device/emulator and reachable test backend, verify app launch, public catalog, email/password sign-in/registration, profile, order history, cart, and simulated checkout including return to the app.
- Confirm that browser login remains cookie-based and that native tokens are not exposed in localStorage.

## Builder calls

- Choose a maintained Capacitor secure-storage plugin compatible with the project's Capacitor version; do not use plain preferences for JWTs.
- Choose and document an appropriate Capacitor deep-link mechanism for the simulated payment return; validate order state on the backend after resuming.
- Document any local Android Studio/JDK/SDK prerequisites and the device-specific API URL setup.
