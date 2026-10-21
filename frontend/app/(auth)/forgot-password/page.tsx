import type { Metadata } from "next";

import { TextLink } from "@/components/text-link";

import { ForgotPasswordForm } from "./forgot-password-form";

export const metadata: Metadata = { title: "Forgot your password · WearWise" };

export default function ForgotPasswordPage() {
  return (
    <>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Forgot your password
      </h1>
      <p className="mt-2 text-ink-soft">
        We&apos;ll send a link to set a new one.
      </p>
      <ForgotPasswordForm />
      <p className="mt-8 text-ink-soft">
        Remembered it? <TextLink href="/login">Log in</TextLink>
      </p>
    </>
  );
}
