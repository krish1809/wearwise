import type { Metadata } from "next";
import { Suspense } from "react";

import { ResetPasswordForm } from "./reset-password-form";

export const metadata: Metadata = { title: "Set a new password · WearWise" };

export default function ResetPasswordPage() {
  return (
    <>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Set a new password
      </h1>
      <Suspense>
        <ResetPasswordForm />
      </Suspense>
    </>
  );
}
