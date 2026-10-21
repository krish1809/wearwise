"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { NETWORK_ERROR, readApiError } from "@/lib/api/errors";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!email.trim()) {
      setProblem("Enter your email address.");
      return;
    }
    setBusy(true);
    setProblem(null);
    try {
      const { error, response } = await api.POST(
        "/api/v1/auth/password-reset",
        {
          body: { email },
        },
      );
      if (response.ok) setSent(true);
      else setProblem(readApiError(error).message);
    } catch {
      setProblem(NETWORK_ERROR);
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="mt-8">
        <Alert>
          If there&apos;s an account for that address, a link to set a new
          password is on its way. It works for an hour.
        </Alert>
      </div>
    );
  }
  return (
    <form noValidate onSubmit={send} className="mt-8 flex flex-col gap-5">
      {problem && <Alert tone="error">{problem}</Alert>}
      <Field label="Email">
        {(control) => (
          <Input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            {...control}
          />
        )}
      </Field>
      <Button type="submit" loading={busy}>
        Send the link
      </Button>
    </form>
  );
}
