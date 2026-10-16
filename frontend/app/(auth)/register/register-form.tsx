"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { NETWORK_ERROR, readApiError } from "@/lib/api/errors";
import { meQueryKey, PASSWORD_MIN_LENGTH } from "@/lib/auth";
import { useSlow, useWarmUpBackend } from "@/lib/hooks";

// The same rules the API checks; checking here first saves a round trip.
const schema = z.object({
  name: z.string().trim().max(100, { error: "Use 100 characters or fewer." }),
  email: z
    .string()
    .trim()
    .pipe(z.email({ error: "Enter an email address like sam@example.com." })),
  password: z.string().min(PASSWORD_MIN_LENGTH, {
    error: `Use at least ${PASSWORD_MIN_LENGTH} characters.`,
  }),
});

type Values = z.infer<typeof schema>;
const FIELDS = ["name", "email", "password"] as const;

export function RegisterForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "", password: "" },
  });
  const slow = useSlow(isSubmitting);
  useWarmUpBackend();

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const { data, error } = await api.POST("/api/v1/auth/register", {
        body: { ...values, name: values.name || null },
      });
      if (data) {
        queryClient.setQueryData(meQueryKey, data);
        router.replace("/onboarding");
        return;
      }
      const problem = readApiError(error);
      const fieldErrors = FIELDS.filter((field) => problem.fields[field]);
      fieldErrors.forEach((field) =>
        setError(field, { message: problem.fields[field] }),
      );
      if (fieldErrors.length === 0) setFormError(problem.message);
    } catch {
      setFormError(NETWORK_ERROR);
    }
  });

  return (
    <form noValidate onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
      {formError && <Alert tone="error">{formError}</Alert>}
      <Field label="Name (optional)" error={errors.name?.message}>
        {(control) => (
          <Input autoComplete="name" {...control} {...register("name")} />
        )}
      </Field>
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
      <Field
        label="Password"
        hint={`At least ${PASSWORD_MIN_LENGTH} characters. A short sentence works well.`}
        error={errors.password?.message}
      >
        {(control) => (
          <Input
            type="password"
            autoComplete="new-password"
            {...control}
            {...register("password")}
          />
        )}
      </Field>
      <Button type="submit" loading={isSubmitting} className="mt-1">
        Create account
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
