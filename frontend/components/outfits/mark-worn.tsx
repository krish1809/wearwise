"use client";

import { Check } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
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
import { problemFrom } from "@/lib/api/errors";
import { dayPhrase, todayIso } from "@/lib/dates";
import { useLogWear } from "@/lib/outfits";

type MarkWornProps = {
  /** What was worn: a saved outfit, or loose items. */
  what: { outfit_id: string } | { item_ids: string[] };
  /** True when it's already logged for today, so the button says so. */
  wornToday?: boolean;
};

/** "I wore this today" in one tap, and another day through a small dialog. */
export function MarkWorn({ what, wornToday = false }: MarkWornProps) {
  const log = useLogWear();

  async function mark(day: string): Promise<string | null> {
    try {
      await log.mutateAsync({ worn_on: day, ...what });
      toast.success(`Marked as worn ${dayPhrase(day)}`);
      return null;
    } catch (error) {
      return problemFrom(error).message;
    }
  }

  return (
    <div className="flex flex-wrap gap-3">
      <Button
        disabled={wornToday}
        loading={log.isPending}
        onClick={async () => {
          const problem = await mark(todayIso());
          if (problem) toast.error(problem);
        }}
      >
        {wornToday ? <Check aria-hidden /> : null}
        {wornToday ? "Worn today" : "I wore this today"}
      </Button>
      <AnotherDay onMark={mark} />
    </div>
  );
}

function AnotherDay({
  onMark,
}: {
  onMark: (day: string) => Promise<string | null>;
}) {
  const [open, setOpen] = useState(false);
  const [day, setDay] = useState(todayIso());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setError(null);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="secondary">Another day</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>When did you wear it?</DialogTitle>
          <DialogDescription>
            Logging an earlier day counts the wear for that day.
          </DialogDescription>
        </DialogHeader>
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={async (event) => {
            event.preventDefault();
            if (!day) {
              setError("Choose a day.");
              return;
            }
            setSaving(true);
            const problem = await onMark(day);
            setSaving(false);
            if (problem) setError(problem);
            else setOpen(false);
          }}
        >
          {error && <Alert tone="error">{error}</Alert>}
          <Field label="Day">
            {(control) => (
              <Input
                type="date"
                value={day}
                max={todayIso()}
                onChange={(event) => setDay(event.target.value)}
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
            <Button type="submit" loading={saving}>
              Mark as worn
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
