import type { Metadata } from "next";
import { Suspense } from "react";

import { DemoButton } from "@/components/demo-button";
import { TextLink } from "@/components/text-link";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Log in · WearWise" };

export default function LoginPage() {
  return (
    <>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Log in
      </h1>
      <Suspense>
        <LoginForm />
      </Suspense>
      <p className="mt-4">
        <TextLink href="/forgot-password">Forgot your password?</TextLink>
      </p>
      <p className="mt-8 text-ink-soft">
        New to WearWise? <TextLink href="/register">Create an account</TextLink>
        , or try a sample wardrobe first:
      </p>
      <div className="mt-3">
        <DemoButton />
      </div>
    </>
  );
}
