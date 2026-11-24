import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import viteConfig, { isCapacitorBuild } from "../../vite.config";

const validationModulePath = resolve(process.cwd(), "scripts/check-android-env.mjs");
const validationModuleUrl = pathToFileURL(validationModulePath);
const androidBuildModulePath = resolve(process.cwd(), "scripts/android-build.mjs");
const androidBuildModuleUrl = pathToFileURL(androidBuildModulePath);

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

describe("Android Capacitor build & PWA configuration", () => {
  afterEach(() => {
    delete process.env.CAPACITOR_BUILD;
  });

  it("disables VitePWA plugins when CAPACITOR_BUILD=1 while keeping them for web production", () => {
    expect(isCapacitorBuild("production", {})).toBe(false);
    expect(isCapacitorBuild("production", { CAPACITOR_BUILD: "1" })).toBe(true);
    expect(isCapacitorBuild("android", {})).toBe(true);

    const resolvePluginNames = (capBuild?: string) => {
      if (capBuild) process.env.CAPACITOR_BUILD = capBuild;
      else delete process.env.CAPACITOR_BUILD;
      const cfg = typeof viteConfig === "function" ? viteConfig({ command: "build", mode: "production" }) : viteConfig;
      return (cfg.plugins ?? [])
        .flat(3)
        .filter((p): p is { name: string } => Boolean(p && typeof p === "object" && "name" in p))
        .map((p) => p.name);
    };

    expect(resolvePluginNames()).toEqual(expect.arrayContaining(["vite-plugin-pwa"]));
    expect(resolvePluginNames("1")).not.toEqual(expect.arrayContaining(["vite-plugin-pwa"]));
  });

  it("resolves cross-platform Gradle commands and uses pnpm in package.json scripts", async () => {
    expect(existsSync(androidBuildModulePath)).toBe(true);
    const mod = await import(androidBuildModuleUrl.href);

    const winCmd = mod.resolveGradleCommand("win32", ["assembleDebug"]);
    expect(winCmd.args).toEqual(["/d", "/s", "/c", "gradlew.bat", "assembleDebug"]);

    const linuxCmd = mod.resolveGradleCommand("linux", ["assembleDebug"]);
    expect(linuxCmd).toEqual({ command: "./gradlew", args: ["assembleDebug"] });

    const pkg = JSON.parse(readFileSync(resolve(process.cwd(), "package.json"), "utf8")) as {
      scripts: Record<string, string>;
    };
    for (const key of ["android:sync", "android:run", "android:build"]) {
      expect(pkg.scripts[key]).not.toContain("npm run");
      expect(pkg.scripts[key]).not.toContain("gradlew.bat");
    }
  });
});
