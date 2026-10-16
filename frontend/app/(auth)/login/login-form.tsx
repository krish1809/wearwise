"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { NETWORK_ERROR, readApiError } from "@/lib/api/errors";
import { meQueryKey, safeNextPath } from "@/lib/auth";
import { useSlow, useWarmUpBackend } from "@/lib/hooks";

const schema = z.object({
  email: z.string().trim().min(1, { error: "Enter your email address." }),
  password: z.string().min(1, { error: "Enter your password." }),
});

type Values = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });
  const slow = useSlow(isSubmitting);
  useWarmUpBackend();

  const sessionEnded = params.get("reason") === "expired";

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const { data, error } = await api.POST("/api/v1/auth/login", {
        body: values,
      });
      if (data) {
        queryClient.setQueryData(meQueryKey, data);
        // Until onboarding is finished or skipped, logging in picks it up again.
        router.replace(
          safeNextPath(
            params.get("next"),
            data.onboarding_completed ? "/home" : "/onboarding",
          ),
        );
        return;
      }
      setFormError(readApiError(error).message);
    } catch {
      setFormError(NETWORK_ERROR);
    }
  });

  return (
    <form noValidate onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
      {formError ? (
        <Alert tone="error">{formError}</Alert>
      ) : (
        sessionEnded && <Alert>Your session has ended. Log in again.</Alert>
      )}
      <Field label="Email" error={errors.email?.message}>
        {(control) => (
          <Input
            type="email"
            autoComplete="email"
            {...control}
            {...register("email")}
          />
        )}
      </Field>
      <Field label="Password" error={errors.password?.message}>
        {(control) => (
          <Input
            type="password"
            autoComplete="current-password"
            {...control}
            {...register("password")}
          />
        )}
      </Field>
      <Button type="submit" loading={isSubmitting} className="mt-1">
        Log in
      </Button>
      {slow && (
        <p role="status" className="text-sm text-ink-soft">
          Waking the server. The first request after a quiet spell can take up
          to a minute.
        </p>
      )}
    </form>
  );
}
