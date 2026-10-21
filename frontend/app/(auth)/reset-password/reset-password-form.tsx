"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { TextLink } from "@/components/text-link";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { NETWORK_ERROR, readApiError } from "@/lib/api/errors";
import { PASSWORD_MIN_LENGTH } from "@/lib/auth";

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (password.length < PASSWORD_MIN_LENGTH) {
      setProblem(`Use at least ${PASSWORD_MIN_LENGTH} characters.`);
      return;
    }
    setBusy(true);
    setProblem(null);
    try {
      const { error, response } = await api.POST(
        "/api/v1/auth/password-reset/confirm",
        { body: { token, password } },
      );
      if (response.ok) setDone(true);
      else setProblem(readApiError(error).message);
    } catch {
      setProblem(NETWORK_ERROR);
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <p className="mt-6">
        This link is missing part of it.{" "}
        <TextLink href="/forgot-password">Ask for a new one</TextLink>
      </p>
    );
  }
  if (done) {
    return (
      <div className="mt-8 flex flex-col gap-4">
        <Alert>
          Your new password is set. Every session was logged out, in case
          someone else had the old one.
        </Alert>
        <p>
          <TextLink href="/login">Log in</TextLink>
        </p>
      </div>
    );
  }
  return (
    <form noValidate onSubmit={save} className="mt-8 flex flex-col gap-5">
      {problem && (
        <Alert tone="error">
          {problem}{" "}
          {problem.includes("expired") && (
            <TextLink href="/forgot-password">Ask for a new link</TextLink>
          )}
        </Alert>
      )}
      <Field
        label="New password"
        hint={`At least ${PASSWORD_MIN_LENGTH} characters.`}
      >
        {(control) => (
          <Input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            {...control}
          />
        )}
      </Field>
      <Button type="submit" loading={busy}>
        Set the password
      </Button>
    </form>
  );
}
