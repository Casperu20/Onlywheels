import { Capacitor } from "@capacitor/core";
import { SecureStorage } from "@aparajita/capacitor-secure-storage";

export interface AuthTokens {
  access: string;
  refresh: string;
}

const TOKEN_KEY = "auth_tokens";
const STORAGE_PREFIX = "onlywheels_";

let storageReady: Promise<void> | null = null;

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

function parseTokens(value: string): AuthTokens {
  const parsed: unknown = JSON.parse(value);
  if (
    typeof parsed !== "object" ||
    parsed === null ||
    !("access" in parsed) ||
    typeof parsed.access !== "string" ||
    parsed.access.length === 0 ||
    !("refresh" in parsed) ||
    typeof parsed.refresh !== "string" ||
    parsed.refresh.length === 0
  ) {
    throw new Error("Stored native authentication credentials are invalid.");
  }
  return { access: parsed.access, refresh: parsed.refresh };
}

export async function getNativeTokens(): Promise<AuthTokens | null> {
  if (!isNativePlatform()) return null;
  await ensureStorageReady();
  const value = await SecureStorage.getItem(TOKEN_KEY);
  return value === null ? null : parseTokens(value);
}

export async function setNativeTokens(tokens: AuthTokens): Promise<void> {
  assertNativePlatform();
  if (
    typeof tokens.access !== "string" ||
    tokens.access.length === 0 ||
    typeof tokens.refresh !== "string" ||
    tokens.refresh.length === 0
  ) {
    throw new Error("Native authentication credentials must include access and refresh tokens.");
  }
  await ensureStorageReady();
  await SecureStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

export async function clearNativeTokens(): Promise<void> {
  assertNativePlatform();
  await ensureStorageReady();
  await SecureStorage.removeItem(TOKEN_KEY);
}
