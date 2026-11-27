import type { Metadata } from "next";
import { Suspense } from "react";

import { ConfirmEmail } from "./confirm-email";

export const metadata: Metadata = { title: "Confirm your address · WearWise" };

export default function ConfirmEmailPage() {
  return (
    <>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Confirm your address
      </h1>
      <Suspense>
        <ConfirmEmail />
      </Suspense>
    </>
  );
}
