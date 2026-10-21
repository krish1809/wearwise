"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { reportError } from "@/lib/report-error";

// A page that broke while showing: say so plainly, report it, and offer to try again.
export default function PageError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => reportError(error), [error]);

  return (
    <div className="mx-auto max-w-xl px-4 py-16">
      <ErrorState
        title="This page didn't load"
        action={
          <Button variant="secondary" onClick={reset}>
            Try again
          </Button>
        }
      >
        Something went wrong on our side, and it has been reported. Try again;
        if it keeps happening, come back a little later.
      </ErrorState>
    </div>
  );
}
