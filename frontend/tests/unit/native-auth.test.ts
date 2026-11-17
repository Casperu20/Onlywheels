// @vitest-environment jsdom

import {
  AxiosError,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { SecureStorage } from "@aparajita/capacitor-secure-storage";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "@/api/http";
import { authApi } from "@/features/auth/api";

const mocks = vi.hoisted(() => ({
  isNativePlatform: vi.fn(),
  setKeyPrefix: vi.fn(),
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
}));

vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: mocks.isNativePlatform },
}));

vi.mock("@aparajita/capacitor-secure-storage", () => ({
  SecureStorage: {
    setKeyPrefix: mocks.setKeyPrefix,
    getItem: mocks.getItem,
    setItem: mocks.setItem,
    removeItem: mocks.removeItem,
  },
}));

const originalAdapter = http.defaults.adapter;
let storedTokens: string | null;

function response(
  config: InternalAxiosRequestConfig,
  data: unknown,
  status = 200,
): AxiosResponse {
  return {
    data,
    status,
    statusText: status === 200 ? "OK" : status === 401 ? "Unauthorized" : "Server Error",
    headers: {},
    config,
  };
}

function rejected(config: InternalAxiosRequestConfig, status = 401): Promise<never> {
  const result = response(config, { detail: "Request failed" }, status);
  return Promise.reject(new AxiosError("Request failed", "ERR_BAD_REQUEST", config, undefined, result));
}

function useAdapter(adapter: AxiosAdapter): void {
  http.defaults.adapter = adapter;
}

describe("native authentication sessions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.isNativePlatform.mockReturnValue(true);
    mocks.setKeyPrefix.mockResolvedValue(undefined);
    storedTokens = JSON.stringify({ access: "access-old", refresh: "refresh-old" });
    mocks.getItem.mockImplementation(async () => storedTokens);
    mocks.setItem.mockImplementation(async (_key: string, value: string) => {
      storedTokens = value;
    });
    mocks.removeItem.mockImplementation(async () => {
      storedTokens = null;
    });
  });

  afterEach(() => {
    http.defaults.adapter = originalAdapter;
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
  });

  it("uses a secure bearer session without cookies or a CSRF preflight", async () => {
    const requests: InternalAxiosRequestConfig[] = [];
    useAdapter(async (config) => {
      requests.push(config);
      return response(config, { ok: true });
    });

    await http.post("/api/v1/orders/");

    expect(requests).toHaveLength(1);
    expect(requests[0].headers.get("Authorization")).toBe("Bearer access-old");
    expect(requests[0].withCredentials).toBe(false);
    expect(requests[0].withXSRFToken).toBe(false);
  });

  it("surfaces secure-storage failures instead of falling back to browser storage", async () => {
    localStorage.setItem("onlywheels.auth.tokens", "must-not-be-read");
    mocks.getItem.mockRejectedValue(new Error("secure storage unavailable"));
    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => response(config, {}));
    useAdapter(adapter);

    await expect(http.get("/api/v1/auth/me/")).rejects.toThrow("secure storage unavailable");

    expect(adapter).not.toHaveBeenCalled();
    expect(localStorage.getItem("onlywheels.auth.tokens")).toBe("must-not-be-read");
  });

  it("stores tokens from native login and returns the user", async () => {
    const requests: InternalAxiosRequestConfig[] = [];
    const user = {
      id: "customer-1",
      email: "customer@example.com",
      first_name: "Ana",
      last_name: "Pop",
      phone: "",
      preferred_language: "ro",
      date_joined: "2026-01-01T00:00:00Z",
      has_password: true,
    };
    useAdapter(async (config) => {
      requests.push(config);
      return response(config, { user, access: "access-new", refresh: "refresh-new" });
    });

    await expect(authApi.login({ email: user.email, password: "safe-test-password" })).resolves.toEqual(user);

    expect(requests.map(({ url }) => url)).toEqual(["/api/v1/auth/native/login/"]);
    expect(JSON.parse(storedTokens ?? "null")).toEqual({ access: "access-new", refresh: "refresh-new" });
  });

  it("uses native registration and persists the returned session", async () => {
    const requests: InternalAxiosRequestConfig[] = [];
    const user = {
      id: "customer-2",
      email: "new-customer@example.com",
      first_name: "Mara",
      last_name: "Ionescu",
      phone: "",
      preferred_language: "ro",
      date_joined: "2026-01-01T00:00:00Z",
      has_password: true,
    };
    useAdapter(async (config) => {
      requests.push(config);
      return response(config, { user, access: "access-new", refresh: "refresh-new" });
    });

    await expect(
      authApi.register({
        email: user.email,
        password: "safe-test-password",
        first_name: user.first_name,
        last_name: user.last_name,
      }),
    ).resolves.toEqual(user);

    expect(requests.map(({ url }) => url)).toEqual(["/api/v1/auth/native/register/"]);
    expect(JSON.parse(storedTokens ?? "null")).toEqual({ access: "access-new", refresh: "refresh-new" });
  });

  it("coalesces concurrent 401 responses into one token refresh and retries each request once", async () => {
    const attempts = new Map<string, number>();
    const requests: InternalAxiosRequestConfig[] = [];
    useAdapter(async (config) => {
      const url = config.url ?? "";
      requests.push(config);
      if (url === "/api/v1/auth/native/refresh/") {
        expect(JSON.parse(config.data as string)).toEqual({ refresh: "refresh-old" });
        return response(config, { access: "access-new", refresh: "refresh-new" });
      }
      if (url.startsWith("/protected/")) {
        const attempt = (attempts.get(url) ?? 0) + 1;
        attempts.set(url, attempt);
        if (attempt === 1) return rejected(config);
      }
      return response(config, { ok: true });
    });

    await Promise.all([http.get("/protected/profile"), http.get("/protected/orders")]);

    expect(requests.filter(({ url }) => url === "/api/v1/auth/native/refresh/")).toHaveLength(1);
    expect(attempts).toEqual(
      new Map([
        ["/protected/profile", 2],
        ["/protected/orders", 2],
      ]),
    );
    expect(JSON.parse(storedTokens ?? "null")).toEqual({ access: "access-new", refresh: "refresh-new" });
  });

  it("clears native credentials after logout even when the server rejects the request", async () => {
    const requests: InternalAxiosRequestConfig[] = [];
    useAdapter(async (config) => {
      requests.push(config);
      if (config.url === "/api/v1/auth/native/logout/") return rejected(config, 500);
      return response(config, {});
    });

    await expect(authApi.logout()).rejects.toMatchObject({ response: { status: 500 } });

    expect(requests.map(({ url }) => url)).toEqual(["/api/v1/auth/native/logout/"]);
    expect(JSON.parse(requests[0].data as string)).toEqual({ refresh: "refresh-old" });
    expect(storedTokens).toBeNull();
  });

  it("clears native credentials when refresh fails and preserves browser cookie/CSRF login", async () => {
    useAdapter(async (config) => {
      if ((config.url ?? "").startsWith("/protected/")) return rejected(config);
      if (config.url === "/api/v1/auth/native/refresh/") return rejected(config);
      return response(config, {});
    });

    await expect(http.get("/protected/profile")).rejects.toMatchObject({ response: { status: 401 } });
    expect(storedTokens).toBeNull();

    vi.clearAllMocks();
    mocks.isNativePlatform.mockReturnValue(false);
    document.cookie = "csrftoken=web-csrf-token; path=/";
    const browserRequests: InternalAxiosRequestConfig[] = [];
    useAdapter(async (config) => {
      browserRequests.push(config);
      return response(config, {
        id: "customer-1",
        email: "customer@example.com",
        first_name: "Ana",
        last_name: "Pop",
        phone: "",
        preferred_language: "ro",
        date_joined: "2026-01-01T00:00:00Z",
        has_password: true,
      });
    });

    await authApi.login({ email: "customer@example.com", password: "safe-test-password" });

    expect(browserRequests.map(({ url }) => url)).toEqual(["/api/v1/auth/login/"]);
    expect(browserRequests[0].withCredentials).toBe(true);
    expect(browserRequests[0].withXSRFToken).toBe(true);
    expect(document.cookie).toContain("csrftoken=web-csrf-token");
    expect(SecureStorage.getItem).not.toHaveBeenCalled();
    expect(SecureStorage.setItem).not.toHaveBeenCalled();
  });
});
