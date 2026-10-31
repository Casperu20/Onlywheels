import { QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, type ReactNode } from "react";
import { Toaster } from "sonner";

import { queryClient } from "@/api/queryClient";
import i18n from "@/i18n";

// Dev only: the devtools chunk is never part of the production bundle.
const ReactQueryDevtools = import.meta.env.DEV
  ? lazy(() =>
      import("@tanstack/react-query-devtools").then((m) => ({ default: m.ReactQueryDevtools })),
    )
  : null;

export function AppProviders({ children }: { children: ReactNode }) {
  useEffect(() => {
    // The API answers in the request language (product descriptions, messages): refetch on switch.
    const refetch = () => void queryClient.invalidateQueries();
    i18n.on("languageChanged", refetch);
    return () => i18n.off("languageChanged", refetch);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster theme="dark" position="top-center" richColors />
      {ReactQueryDevtools && (
        <Suspense fallback={null}>
          <ReactQueryDevtools buttonPosition="bottom-left" />
        </Suspense>
      )}
    </QueryClientProvider>
  );
}
