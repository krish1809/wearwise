"use client";

import { useEffect } from "react";

import { reportError } from "@/lib/report-error";

import "./globals.css";

// The last resort, when even the page's frame failed: it replaces the whole document.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => reportError(error), [error]);

  return (
    <html lang="en">
      <body className="bg-paper text-ink">
        <main className="mx-auto flex max-w-xl flex-col items-start gap-4 px-4 py-16">
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            WearWise didn&apos;t load
          </h1>
          <p className="text-ink-soft">
            Something went wrong on our side, and it has been reported.
          </p>
          <button
            type="button"
            onClick={reset}
            className="min-h-11 rounded-lg bg-ink px-4 font-medium text-on-ink"
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
