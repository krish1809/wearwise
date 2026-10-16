import type { Metadata } from "next";

import { TextLink } from "@/components/text-link";

import { RegisterForm } from "./register-form";

export const metadata: Metadata = { title: "Create an account · WearWise" };

export default function RegisterPage() {
  return (
    <>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Create an account
      </h1>
      <p className="mt-3 text-ink-soft">
        An email and a password are all it takes. Everything else is optional
        and can wait.
      </p>
      <RegisterForm />
      <p className="mt-8 text-ink-soft">
        Already have an account? <TextLink href="/login">Log in</TextLink>
      </p>
    </>
  );
}
