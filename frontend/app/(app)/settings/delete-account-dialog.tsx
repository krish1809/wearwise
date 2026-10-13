"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api/client";
import { NETWORK_ERROR, readApiError } from "@/lib/api/errors";

/** Deleting needs the account's email typed out, so it can't happen by accident. */
export function DeleteAccountDialog({ email }: { email: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const matches = typed.trim().toLowerCase() === email;

  function changeOpen(next: boolean) {
    setOpen(next);
    if (!next) {
      setTyped("");
      setError(null);
    }
  }

  async function deleteAccount() {
    setDeleting(true);
    setError(null);
    try {
      const { error: apiError, response } = await api.POST(
        "/api/v1/account/delete",
        {
          body: { confirm_email: typed },
        },
      );
      if (response.ok) {
        queryClient.clear();
        router.replace("/");
        toast.success("Your account has been deleted.");
        return;
      }
      setError(readApiError(apiError).message);
    } catch {
      setError(NETWORK_ERROR);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive">Delete account</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete your account?</DialogTitle>
          <DialogDescription>
            Your account and everything in it will be removed. This can&apos;t
            be undone.
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (matches) void deleteAccount();
          }}
        >
          <Field label={`Type ${email} to confirm`} error={error ?? undefined}>
            {(control) => (
              <Input
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                {...control}
              />
            )}
          </Field>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button
              type="submit"
              variant="destructive"
              disabled={!matches}
              loading={deleting}
            >
              Delete account
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
