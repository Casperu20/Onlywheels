import axios, { type AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from "axios";

import i18n from "@/i18n";
import { clearNativeTokens, getNativeTokens, isNativePlatform, setNativeTokens } from "@/lib/native";

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: { Accept: "application/json" },
});

// Django needs the `csrftoken` cookie for every unsafe request; fetch it lazily once (deduplicated).
const SAFE_METHODS = ["get", "head", "options"];
let csrfReady = false;
let csrfPromise: Promise<void> | null = null;

function ensureCsrfToken(): Promise<void> {
  if (csrfReady || document.cookie.includes("csrftoken=")) {
    csrfReady = true;
    return Promise.resolve();
  }
  csrfPromise ??= http
    .get("/api/v1/csrf/")
    .then(() => {
      csrfReady = true;
    })
    .finally(() => {
      csrfPromise = null;
    });
  return csrfPromise;
}

http.interceptors.request.use(async (config) => {
  config.headers.set("Accept-Language", i18n.language || "ro");
  if (isNativePlatform()) {
    const tokens = await getNativeTokens();
    config.withCredentials = false;
    config.withXSRFToken = false;
    if (tokens) config.headers.set("Authorization", `Bearer ${tokens.access}`);
    return config;
  }
  const method = (config.method ?? "get").toLowerCase();
  if (!SAFE_METHODS.includes(method)) {
    await ensureCsrfToken();
  }
  return config;
});

// Calls that must never trigger the "refresh and retry" logic below.
const NO_RETRY = [
  "/auth/login/",
  "/auth/register/",
  "/auth/google/",
  "/auth/refresh/",
  "/auth/logout/",
  "/auth/native/login/",
  "/auth/native/register/",
  "/auth/native/refresh/",
  "/auth/native/logout/",
];

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

let refreshing: Promise<void> | null = null;

function refreshSession(): Promise<void> {
  if (isNativePlatform()) {
    refreshing ??= getNativeTokens().then((tokens) => {
      if (!tokens) throw new Error("Native authentication session is missing.");
      return http
        .post<{ access: string; refresh: string }>("/api/v1/auth/native/refresh/", { refresh: tokens.refresh })
        .then(({ data }) => setNativeTokens(data));
    }).finally(() => {
      refreshing = null;
    });
    return refreshing;
  }
  refreshing ??= http
    .post("/api/v1/auth/refresh/")
    .then(() => undefined)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const url = config?.url ?? "";
    const canRetry =
      error.response?.status === 401 && config && !config._retried && !NO_RETRY.some((p) => url.includes(p));

    if (!canRetry) return Promise.reject(error);

    config._retried = true;
    try {
      await refreshSession();
    } catch {
      if (isNativePlatform()) {
        await clearNativeTokens();
      }
      return Promise.reject(error);
    }
    return http(config);
  },
);

/** Mutator used by the orval-generated client (see orval.config.ts). */
export const apiClient = <T>(config: AxiosRequestConfig, options?: AxiosRequestConfig): Promise<T> =>
  http<T>({ ...config, ...options }).then(({ data }) => data);

export type ErrorType<E> = AxiosError<E>;
export type BodyType<B> = B;
