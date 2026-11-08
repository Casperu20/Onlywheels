import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { loadEnv, type Plugin } from "vite";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

// Draco decoder for compressed showroom GLBs, served from our origin (CSP) and pinned to the installed three.
const DRACO_DIR = fileURLToPath(new URL("./node_modules/three/examples/jsm/libs/draco/gltf/", import.meta.url));
const DRACO_FILES = ["draco_decoder.js", "draco_decoder.wasm", "draco_wasm_wrapper.js"];

function dracoDecoder(): Plugin {
  return {
    name: "onlywheels-draco-decoder",
    configureServer(server) {
      server.middlewares.use("/draco", (req, res, next) => {
        const name = (req.url ?? "").split("?")[0].replace(/^\//, "");
        if (!DRACO_FILES.includes(name)) return next();
        res.setHeader("Content-Type", name.endsWith(".wasm") ? "application/wasm" : "text/javascript");
        res.end(readFileSync(DRACO_DIR + name));
      });
    },
    generateBundle() {
      for (const name of DRACO_FILES) {
        this.emitFile({ type: "asset", fileName: `draco/${name}`, source: readFileSync(DRACO_DIR + name) });
      }
    },
  };
}

// Installable PWA: app shell precached, catalog API network-first (offline fallback), media cache-first.
const pwa = VitePWA({
  registerType: "autoUpdate",
  includeAssets: ["onlywheels-logo.svg", "apple-touch-icon.png"],
  manifest: {
    name: "OnlyWheels",
    short_name: "OnlyWheels",
    description: "Jante, anvelope și roți complete, cu montaj la service-uri partenere.",
    lang: "ro",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#101113",
    theme_color: "#101113",
    icons: [
      { src: "pwa-192.png", sizes: "192x192", type: "image/png" },
      { src: "pwa-512.png", sizes: "512x512", type: "image/png" },
      { src: "pwa-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  },
  workbox: {
    navigateFallback: "/index.html",
    // The 3D viewer chunk and the Draco decoder are large and only needed in the showroom: load on demand.
    globIgnores: ["draco/**", "assets/ModelCanvas-*.js"],
    navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/media\//, /^\/static\//],
    runtimeCaching: [
      {
        urlPattern: ({ url }) => url.pathname.startsWith("/api/v1/catalog/"),
        handler: "NetworkFirst",
        options: {
          cacheName: "api-catalog",
          networkTimeoutSeconds: 4,
          expiration: { maxEntries: 100, maxAgeSeconds: 24 * 60 * 60 },
        },
      },
      {
        urlPattern: ({ url }) => url.pathname.startsWith("/media/"),
        handler: "CacheFirst",
        options: {
          cacheName: "media",
          expiration: { maxEntries: 200, maxAgeSeconds: 30 * 24 * 60 * 60 },
        },
      },
    ],
  },
});

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react(), tailwindcss(), dracoDecoder(), mode === "test" ? [] : pwa],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      port: 5173,
      // Same-origin in dev: the browser only talks to Vite, so auth cookies + CSRF just work.
      proxy: {
        "/api": { target: backend },
        "/media": { target: backend },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./tests/setup.ts"],
      include: ["tests/**/*.test.{ts,tsx}", "src/**/*.test.{ts,tsx}"],
      css: false,
    },
  };
});
