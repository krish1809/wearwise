"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { reportError } from "@/lib/report-error";

// TanStack Query caches what the API returns (who is logged in, and later the wardrobe),
// and handles loading and error states.
export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
      }),
  );
  // Errors nothing else caught are reported, so the owner hears about them.
  useEffect(() => {
    const onError = (event: ErrorEvent) =>
      reportError(event.error ?? event.message);
    const onRejection = (event: PromiseRejectionEvent) =>
      reportError(event.reason);
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
