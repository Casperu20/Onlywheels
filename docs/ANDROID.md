# Android app – remaining steps

**University demo scope:** the target is an installable debug app with test accounts, demo data, and simulated
payments, not a commercial release. Real merchant accounts and Play Store publication are not required.

The implemented scope covers the Capacitor shell, native email/password sessions stored in secure storage, and
simulated checkout returning through `onlywheels://checkout/success`. Android build, installation, and device
acceptance are still unverified. They need a reachable backend, Android tools, and a device/emulator; a commercial
hosting setup is not required, although the current Android preflight still requires an HTTPS backend URL.

Work through the sections in order and tick the boxes as you go. The detailed reference is in
[SETUP.md – Android debug app](./SETUP.md#android-debug-app-capacitor); the implementation plan is in
[plans/2026-11-15-android-app.md](./superpowers/plans/2026-11-15-android-app.md).

## Status at a glance

| Area | Status |
|---|---|
| Capacitor project (`frontend/android`, app id `ro.onlywheels.app`) | Done |
| Native JWT endpoints (`/api/v1/auth/native/...`) | Done, tested |
| Secure token storage, bearer auth, refresh | Done, tested |
| Deep link `onlywheels://checkout/success?order=...` | Done, tested |
| Android tools installed | **To do** – step 1 |
| HTTPS backend reachable from the phone | **To do** – step 2 |
| `VITE_API_URL` configured | **To do** – step 3 |
| First build and install | **To do** – step 4 |
| Testing on the device | **To do** – step 5 |
| Push notifications, Google sign-in in the app, Play Store | Optional extensions - step 7 |

## 1. Install the Android tools (one time)

- [ ] Node.js 22 or newer: `node --version`
- [ ] Install Android Studio 2025.2.1 or newer. It includes the JDK that Gradle uses.
- [ ] In Android Studio → **SDK Manager**, install:
  - [ ] Android SDK Platform 36
  - [ ] Android SDK Platform-Tools
- [ ] Add the `platform-tools` folder to `PATH` (usually
      `%LOCALAPPDATA%\Android\Sdk\platform-tools`), then open a new terminal.
- [ ] Get a device:
  - Emulator: Android Studio → **Device Manager** → create and start a virtual device, or
  - Phone: enable Developer options and USB debugging, connect it by cable and accept the prompt on the phone.
- [ ] Check that the device is listed:

  ```powershell
  adb devices
  ```

  You should see one line ending in `device` (not `unauthorized` or `offline`).

## 2. Make the backend reachable over HTTPS

The app runs on the phone, so `localhost` means the phone, not your computer. The app also only accepts HTTPS.
Pick one option:

- [ ] **Option A – deployed staging/dev backend** with a valid certificate (for example the Phase 1 deployment).
- [ ] **Option B – your local backend through an HTTPS tunnel** (for example Cloudflare Tunnel or ngrok). Start
      Django locally, point the tunnel at `http://localhost:8000`, and note the `https://...` address it gives you.

Do not use a self-signed certificate and do not turn off TLS checks.

Then update `backend/.env` on the machine that runs that backend:

- [ ] Keep `FRONTEND_URL` as the normal web address (for example `http://localhost:5173`).
- [ ] Allow the app's WebView origin in CORS, next to the web origin:

  ```dotenv
  CORS_ALLOWED_ORIGINS=http://localhost:5173,https://localhost
  ```

- [ ] Add the backend's public hostname (no `https://`, no port) to `DJANGO_ALLOWED_HOSTS`, for example:

  ```dotenv
  DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,abc123.trycloudflare.com
  ```

- [ ] For testing checkout without a payment account: `PAYMENT_PROVIDER=fake` (development only – production
      refuses it).
- [ ] Restart Django.
- [ ] Check from the phone's browser that `https://<your-backend>/api/v1/health/` responds. If the phone cannot open it, the
      app cannot either.

## 3. Point the app at the backend

From `frontend`:

```powershell
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
notepad .env.local
```

- [ ] Set the backend origin, without `/api/v1` and without a trailing slash:

  ```dotenv
  VITE_API_URL=https://abc123.trycloudflare.com
  ```

The build refuses empty, non-HTTPS, malformed and `localhost`/`127.0.0.1`/`::1` values. `.env.local` stays on your
machine and is not committed. If you use a quick tunnel, its address changes each time it restarts – update this value
and rebuild when it does.

## 4. Build and install

From `frontend`:

```powershell
corepack pnpm install        # first time, or after dependency changes
corepack pnpm android:sync   # checks VITE_API_URL, builds the web app, copies it into the Android project
corepack pnpm android:run    # builds, installs and starts the app on the device
```

- [ ] `android:sync` finishes without errors.
- [ ] `android:run` installs the app and OnlyWheels opens on the device.
- [ ] The OnlyWheels icon appears in the app drawer and opens the app.

Optional – make an APK file to share or install by hand:

```powershell
corepack pnpm android:build
adb install -r android\app\build\outputs\apk\debug\app-debug.apk
```

Run `android:sync` again whenever frontend code, `.env.local` or the Android manifest changes.

## 5. Test on the device

Use test accounts and the fake payment provider only.

**Catalog and account**

- [ ] The catalog loads and images show.
- [ ] Register a new account with email and password; the profile shows the new user.
- [ ] Close the app completely and open it again – you are still signed in.
- [ ] Log out, then log in again with the same account.
- [ ] The **Continue with Google** button is not shown in the app (expected for now).

**Cart and checkout**

- [ ] Add a product to the cart; the cart survives closing and reopening the app.
- [ ] Place an order and reach the in-app fake payment page.
- [ ] Complete the fake payment; the app opens the order success page.
- [ ] The success page shows the order as paid (the status comes from the backend).
- [ ] The order appears in account order history.

**Deep links** – replace the order number with a real order of the signed-in user:

- [ ] App open (warm start):

  ```powershell
  adb shell am start -a android.intent.action.VIEW `
    -d "onlywheels://checkout/success?order=OW260615-ABC123" ro.onlywheels.app
  ```

  The success page shows that order's real status.
- [ ] App closed (cold start): close the app from recent apps, run the same command, same result.
- [ ] An unpaid order opened this way is **not** shown as paid – the link alone never marks a payment.
- [ ] Wrong links do not open the success page, for example:

  ```powershell
  adb shell am start -a android.intent.action.VIEW -d "onlywheels://checkout/other?order=OW260615-ABC123" ro.onlywheels.app
  adb shell am start -a android.intent.action.VIEW -d "onlywheels://checkout/success" ro.onlywheels.app
  ```

**Web still works** – on the computer, in the browser:

- [ ] Login, logout and checkout on the web site behave as before.

## 6. Close out

- [ ] Tick Task 1 Step 7, Task 4 Step 6 and Task 5 Step 2 in
      [plans/2026-11-15-android-app.md](./superpowers/plans/2026-11-15-android-app.md).
- [ ] Mark the Android debug build as verified in [ROADMAP.md](./ROADMAP.md).
- [ ] Write down anything that behaved differently from this list and fix it before moving on.

## 7. Optional extensions (outside the current university demo)

These are not unfinished requirements for the university demo. Consider them only if explicitly chosen for an
additional demonstration or required by the coursework:

- **Push notifications (FCM)** – Firebase project, `google-services.json`, device token registration in the backend,
  sending order-status notifications.
- **Google sign-in in the app** – native Google login flow; the web Google login does not work inside the app.
- **Real payments in the app** – Stripe/NETOPIA return URLs that come back into the app instead of the web site.
- **Play Store release** – app icon and splash screen, release signing key (kept out of the repository), version
  numbers, privacy policy, store listing, internal testing track.

## Troubleshooting

| Problem | What to check |
|---|---|
| `VITE_API_URL is required` or rejected | `frontend/.env.local` exists and holds an `https://` address that is not `localhost`. |
| App opens but the catalog is empty or shows errors | Open the backend URL in the phone's browser; check `https://localhost` is in `CORS_ALLOWED_ORIGINS`, the hostname is in `DJANGO_ALLOWED_HOSTS`, and Django was restarted. |
| Worked yesterday, fails today with a tunnel | The tunnel address changed – update `VITE_API_URL` and `DJANGO_ALLOWED_HOSTS`, restart Django, run `android:sync` again. |
| `adb` not recognized / no devices | Install Platform-Tools, fix `PATH`, open a new terminal; accept the USB debugging prompt on the phone. |
| Gradle cannot find the SDK | Open `frontend\android` in Android Studio once so it creates `local.properties`, then retry. |
| Fake payment not offered | The backend needs `PAYMENT_PROVIDER=fake`. |
| Deep link does not open the app | Run `android:sync` and reinstall; check the link is exactly `onlywheels://checkout/success?order=...`. |
| Signed out after every restart | Secure storage or token refresh failed – look for errors in Android Studio's Logcat and check the backend logs for `/auth/native/refresh/`. |
