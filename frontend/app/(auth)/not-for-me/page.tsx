import type { Metadata } from "next";
import { Suspense } from "react";

import { NotForMe } from "./not-for-me";

export const metadata: Metadata = { title: "Not for me · WearWise" };

export default function NotForMePage() {
  return (
    <>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Not for me
      </h1>
      <p className="mt-2 text-ink-soft">
        That trend won&apos;t be picked for you again, and picks of the same
        kind and colour will come up less.
      </p>
      <Suspense>
        <NotForMe />
      </Suspense>
    </>
  );
}
