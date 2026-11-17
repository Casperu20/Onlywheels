import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const validationModulePath = resolve(process.cwd(), "scripts/check-android-env.mjs");
const validationModuleUrl = pathToFileURL(validationModulePath);

async function loadValidator() {
  expect(existsSync(validationModulePath)).toBe(true);
  const module = await import(validationModuleUrl.href);
  return module.validateAndroidApiUrl;
}

describe("validateAndroidApiUrl", () => {
  it("accepts a reachable HTTPS API URL", async () => {
    const validate = await loadValidator();

    expect(validate("https://api.example.test/v1/").href).toBe("https://api.example.test/v1/");
  });

  it("rejects a missing API URL", async () => {
    const validate = await loadValidator();

    expect(() => validate(undefined)).toThrow(/VITE_API_URL/);
  });

  it("rejects a malformed API URL", async () => {
    const validate = await loadValidator();

    expect(() => validate("not-a-url")).toThrow(/VITE_API_URL/);
  });

  it.each(["localhost", "127.0.0.1", "::1"])("rejects loopback host %s", async (host) => {
    const validate = await loadValidator();
    const urlHost = host.includes(":") ? `[${host}]` : host;

    expect(() => validate(`https://${urlHost}/api`)).toThrow(/loopback/);
  });
});
