import type { Metadata } from "next";
import { Suspense } from "react";

import { Unsubscribe } from "./unsubscribe";

export const metadata: Metadata = { title: "Unsubscribe · WearWise" };

export default function UnsubscribePage() {
  return (
    <>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Stop the weekly email
      </h1>
      <p className="mt-2 text-ink-soft">
        Your account and your picks stay as they are; only the email stops.
      </p>
      <Suspense>
        <Unsubscribe />
      </Suspense>
    </>
  );
}
