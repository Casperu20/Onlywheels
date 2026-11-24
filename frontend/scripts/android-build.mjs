import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export function buildCapacitorEnv(baseEnv = process.env) {
  return {
    ...baseEnv,
    CAPACITOR_BUILD: "1",
  };
}

export function resolveGradleCommand(platform = process.platform, args = ["assembleDebug"]) {
  const safeArgs = args.length > 0 ? args : ["assembleDebug"];
  if (platform === "win32") {
    return {
      command: process.env.ComSpec || "cmd.exe",
      args: ["/d", "/s", "/c", "gradlew.bat", ...safeArgs],
    };
  }
  return {
    command: "./gradlew",
    args: safeArgs,
  };
}

async function runAndroidWebBuild() {
  const env = buildCapacitorEnv(process.env);
  process.env.CAPACITOR_BUILD = "1";

  const tscBin = resolve(process.cwd(), "node_modules/typescript/bin/tsc");
  const tscResult = spawnSync(process.execPath, [tscBin, "--noEmit"], {
    stdio: "inherit",
    env,
  });
  if (tscResult.status !== 0) {
    process.exitCode = tscResult.status ?? 1;
    return;
  }

  const { build } = await import("vite");
  await build({ mode: "production" });
}

function runAndroidGradle(gradleArgs) {
  const androidDir = resolve(process.cwd(), "android");
  const { command, args } = resolveGradleCommand(process.platform, gradleArgs);
  const result = spawnSync(command, args, {
    cwd: androidDir,
    stdio: "inherit",
    env: process.env,
  });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exitCode = result.status ?? 1;
  }
}

async function main() {
  const [subcommand, ...rest] = process.argv.slice(2);
  if (subcommand === "web") {
    await runAndroidWebBuild();
    return;
  }
  if (subcommand === "gradle") {
    runAndroidGradle(rest);
    return;
  }
  throw new Error("Usage: node scripts/android-build.mjs <web|gradle> [args...]");
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
