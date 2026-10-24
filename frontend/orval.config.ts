import { defineConfig } from "orval";

// Run `pnpm api:generate` while the Django dev server is running.
export default defineConfig({
  onlywheels: {
    input: {
      target: process.env.OPENAPI_URL ?? "http://127.0.0.1:8000/api/schema/",
    },
    output: {
      mode: "tags-split",
      target: "src/api/generated/endpoints",
      schemas: "src/api/generated/model",
      client: "react-query",
      mock: true,
      clean: true,
      override: {
        mutator: { path: "src/api/http.ts", name: "apiClient" },
      },
    },
  },
});
