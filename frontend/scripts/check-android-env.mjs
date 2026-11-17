import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const validationError =
  "VITE_API_URL is required for Android builds and must be an absolute HTTPS URL reachable from the device.";

export function validateAndroidApiUrl(value) {
  if (!value?.trim()) {
    throw new Error(validationError);
  }

  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(validationError);
  }

  if (url.protocol !== "https:" || !url.hostname) {
    throw new Error(validationError);
  }

  const hostname = url.hostname.toLowerCase().replace(/^\[|\]$/g, "").replace(/\.$/, "");
  const isLoopback = hostname === "localhost" || hostname.endsWith(".localhost") || hostname === "::1" || /^127\./.test(hostname);
  if (isLoopback) {
    throw new Error("VITE_API_URL must not point to localhost or a loopback address; use a device-reachable backend URL.");
  }

  return url;
}

async function runPreflight() {
  const { loadEnv } = await import("vite");
  const { VITE_API_URL } = loadEnv("production", process.cwd(), "");
  validateAndroidApiUrl(VITE_API_URL);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  runPreflight().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
