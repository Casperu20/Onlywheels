import { Capacitor } from "@capacitor/core";
import { SecureStorage } from "@aparajita/capacitor-secure-storage";

export interface AuthTokens {
  access: string;
  refresh: string;
}

const TOKEN_KEY = "auth_tokens";
const STORAGE_PREFIX = "onlywheels_";

let storageReady: Promise<void> | null = null;
let cachedTokens: AuthTokens | null = null;
let isHydrated = false;
let hydrationPromise: Promise<AuthTokens | null> | null = null;

export function isNativePlatform(): boolean {
  return Capacitor.isNativePlatform();
}

function assertNativePlatform(): void {
  if (!isNativePlatform()) {
    throw new Error("Secure authentication storage is only available on a native platform.");
  }
}

async function ensureStorageReady(): Promise<void> {
  if (!storageReady) {
    storageReady = SecureStorage.setKeyPrefix(STORAGE_PREFIX).catch((error: unknown) => {
      storageReady = null;
      throw error;
    });
  }
  await storageReady;
}

function tryParseTokens(value: string): AuthTokens | null {
  try {
    const parsed: unknown = JSON.parse(value);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "access" in parsed &&
      typeof (parsed as { access: unknown }).access === "string" &&
      (parsed as { access: string }).access.trim().length > 0 &&
      "refresh" in parsed &&
      typeof (parsed as { refresh: unknown }).refresh === "string" &&
      (parsed as { refresh: string }).refresh.trim().length > 0
    ) {
      return {
        access: (parsed as { access: string }).access,
        refresh: (parsed as { refresh: string }).refresh,
      };
    }
  } catch {
    // Malformed JSON (corrupted storage entry)
  }
  return null;
}

export async function getNativeTokens(): Promise<AuthTokens | null> {
  if (!isNativePlatform()) return null;
  if (isHydrated) return cachedTokens;

  if (hydrationPromise) {
    return await hydrationPromise;
  }

  hydrationPromise = (async () => {
    await ensureStorageReady();
    const value = await SecureStorage.getItem(TOKEN_KEY);
    if (value === null) {
      cachedTokens = null;
      isHydrated = true;
      return null;
    }

    const tokens = tryParseTokens(value);
    if (!tokens) {
      // Self-heal: stored data is corrupted or fails validation.
      // Evict the bad key so the app is not permanently bricked.
      await SecureStorage.removeItem(TOKEN_KEY).catch(() => undefined);
      cachedTokens = null;
      isHydrated = true;
      return null;
    }

    cachedTokens = tokens;
    isHydrated = true;
    return tokens;
  })().finally(() => {
    hydrationPromise = null;
  });

  return await hydrationPromise;
}

export async function setNativeTokens(tokens: AuthTokens): Promise<void> {
  assertNativePlatform();
  if (
    typeof tokens.access !== "string" ||
    tokens.access.trim().length === 0 ||
    typeof tokens.refresh !== "string" ||
    tokens.refresh.trim().length === 0
  ) {
    throw new Error("Native authentication credentials must include access and refresh tokens.");
  }
  await ensureStorageReady();
  await SecureStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  cachedTokens = { access: tokens.access, refresh: tokens.refresh };
  isHydrated = true;
}

export async function clearNativeTokens(): Promise<void> {
  assertNativePlatform();
  await ensureStorageReady();
  try {
    await SecureStorage.removeItem(TOKEN_KEY);
  } finally {
    cachedTokens = null;
    isHydrated = true;
  }
}

export function resetNativeTokenCacheForTests(): void {
  cachedTokens = null;
  isHydrated = false;
  hydrationPromise = null;
  storageReady = null;
}
