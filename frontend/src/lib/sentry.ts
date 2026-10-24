/**
 * Error tracking with Sentry, enabled only when VITE_SENTRY_DSN is set.
 * The SDK is imported on demand, so it costs nothing in the bundle when disabled.
 */
type SentryModule = typeof import("@sentry/react");

let sentry: Promise<SentryModule> | null = null;

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn || sentry) return;
  sentry = import("@sentry/react").then((Sentry) => {
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE,
      integrations: [Sentry.browserTracingIntegration()],
      tracesSampleRate: 0.1,
    });
    return Sentry;
  });
}

export function reportError(error: unknown) {
  if (sentry) void sentry.then((Sentry) => Sentry.captureException(error));
  else if (import.meta.env.DEV) console.error(error);
}
