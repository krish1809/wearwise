"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api/client";
import { ApiRequestError, problemFrom, readApiError } from "@/lib/api/errors";
import { meQueryKey, type User } from "@/lib/auth";

/** The name WearWise greets the person with. Blank clears it. */
export function NameForm({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(user.name ?? "");
  const [error, setError] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: async (value: string | null) => {
      const { data, error: apiError } = await api.PATCH("/api/v1/account", {
        body: { name: value },
      });
      if (data) return data;
      throw new ApiRequestError(readApiError(apiError));
    },
    onSuccess: (saved) => queryClient.setQueryData(meQueryKey, saved),
  });

  return (
    <form
      noValidate
      className="flex flex-col gap-4 sm:flex-row sm:items-start"
      onSubmit={(event) => {
        event.preventDefault();
        setError(null);
        save.mutate(name.trim() || null, {
          onSuccess: () => toast.success("Name saved"),
          onError: (failure) => {
            const problem = problemFrom(failure);
            setError(problem.fields.name ?? problem.message);
          },
        });
      }}
    >
      <Field
        label="Name (optional)"
        error={error ?? undefined}
        className="sm:max-w-sm sm:flex-1"
      >
        {(control) => (
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoComplete="name"
            maxLength={100}
            {...control}
          />
        )}
      </Field>
      <Button
        type="submit"
        variant="secondary"
        loading={save.isPending}
        className="self-start sm:mt-7"
      >
        Save name
      </Button>
    </form>
  );
}
