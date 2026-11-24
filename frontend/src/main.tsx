import "@/i18n";
import "@/styles/globals.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";

import { AppProviders } from "@/app/providers";
import { router } from "@/app/router";
import { installStaleChunkReload } from "@/lib/chunkReload";
import { isNativePlatform, registerDeepLinkListener } from "@/lib/native";
import { initSentry } from "@/lib/sentry";

initSentry();
installStaleChunkReload();

if (isNativePlatform()) {
  if ("serviceWorker" in navigator) {
    void navigator.serviceWorker
      .getRegistrations()
      .then((registrations) => Promise.all(registrations.map((reg) => reg.unregister())))
      .catch(() => undefined);
  }
  void registerDeepLinkListener((path) => {
    void router.navigate(path, { replace: true }).catch((error: unknown) =>
      console.error("Could not navigate from a deep link.", error),
    );
  }).catch((error: unknown) => console.error("Could not register the deep-link listener.", error));
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </StrictMode>,
);
