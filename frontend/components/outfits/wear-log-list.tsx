"use client";

import Link from "next/link";
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
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { problemFrom } from "@/lib/api/errors";
import { dayLabel, dayPhrase, todayIso } from "@/lib/dates";
import {
  type WearLog,
  type WearLogFilters,
  useDeleteWearLog,
  useUpdateWearLog,
  useWearLogs,
} from "@/lib/outfits";
import type { Reference } from "@/lib/profile";
import { listed } from "@/lib/text";
import { cn, focusRing } from "@/lib/utils";

type WearLogListProps = {
  filters: WearLogFilters;
  reference: Reference;
  /** Shown when nothing has been logged. */
  empty: React.ReactNode;
};

/** What was worn, grouped by day, newest first; each entry can be changed or deleted. */
export function WearLogList({ filters, reference, empty }: WearLogListProps) {
  const logs = useWearLogs(filters);
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const occasionNames = new Map(reference.occasions.map((o) => [o.id, o.name]));

  if (logs.isError) {
    return (
      <ErrorState
        title="Couldn't load the wear log"
        action={
          <Button variant="secondary" onClick={() => void logs.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!logs.data) {
    return (
      <div aria-busy="true" className="flex flex-col gap-3">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <span role="status" className="sr-only">
          Loading
        </span>
      </div>
    );
  }
  const all = logs.data.pages.flatMap((page) => page.logs);
  if (all.length === 0) return <>{empty}</>;

  const days: [string, WearLog[]][] = [];
  for (const log of all) {
    const last = days.at(-1);
    if (last && last[0] === log.worn_on) last[1].push(log);
    else days.push([log.worn_on, [log]]);
  }

  return (
    <div className="flex flex-col gap-6">
      {days.map(([day, entries]) => (
        <section key={day} aria-labelledby={`day-${day}`}>
          <h3
            id={`day-${day}`}
            className="mb-2 text-sm font-medium text-ink-soft"
          >
            {dayLabel(day)}
          </h3>
          <ul className="flex flex-col gap-2">
            {entries.map((log) => (
              <li key={log.id}>
                <Entry
                  log={log}
                  familyHex={familyHex}
                  occasionName={
                    log.occasion_id
                      ? occasionNames.get(log.occasion_id)
                      : undefined
                  }
                  reference={reference}
                />
              </li>
            ))}
          </ul>
        </section>
      ))}
      {logs.hasNextPage && (
        <Button
          variant="secondary"
          className="self-center"
          loading={logs.isFetchingNextPage}
          onClick={() => void logs.fetchNextPage()}
        >
          Show earlier days
        </Button>
      )}
    </div>
  );
}

function Entry({
  log,
  familyHex,
  occasionName,
  reference,
}: {
  log: WearLog;
  familyHex: Map<string, string | null>;
  occasionName?: string;
  reference: Reference;
}) {
  const title = log.outfit_name ?? listed(log.pieces.map((p) => p.name));
  return (
    <div className="flex flex-col gap-3 rounded-lg bg-surface p-3 sm:flex-row sm:items-center">
      <ul aria-label="What was worn" className="flex shrink-0 gap-1.5">
        {log.pieces.slice(0, 5).map((piece) => (
          <li
            key={`${piece.slot}-${piece.name}`}
            className={cn(
              "flex size-12 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full",
              piece.removed && "border border-dashed border-line-strong",
            )}
          >
            {piece.item ? (
              <ItemPhoto
                photo={piece.item.photo}
                alt={piece.name}
                hex={
                  piece.item.color_hex ??
                  familyHex.get(piece.item.color_primary)
                }
              />
            ) : (
              <span className="sr-only">{piece.name}, deleted</span>
            )}
          </li>
        ))}
        {log.pieces.length > 5 && (
          <li className="flex size-12 items-center justify-center text-sm text-ink-soft">
            +{log.pieces.length - 5}
          </li>
        )}
      </ul>
      <div className="min-w-0 flex-1">
        {log.outfit_id ? (
          <Link
            href={`/outfits/${log.outfit_id}`}
            className={cn(
              "block truncate rounded font-medium hover:underline",
              focusRing,
            )}
          >
            {title}
          </Link>
        ) : (
          <p className="truncate font-medium">{title}</p>
        )}
        <p className="truncate text-sm text-ink-soft">
          {[occasionName, log.note].filter(Boolean).join(" · ") ||
            `${log.pieces.length} ${log.pieces.length === 1 ? "piece" : "pieces"}`}
        </p>
      </div>
      <div className="flex gap-2">
        <EditEntry log={log} reference={reference} />
        <DeleteEntry log={log} title={title} />
      </div>
    </div>
  );
}

function EditEntry({ log, reference }: { log: WearLog; reference: Reference }) {
  const update = useUpdateWearLog(log.id);
  const [open, setOpen] = useState(false);
  const [day, setDay] = useState(log.worn_on);
  const [occasion, setOccasion] = useState(log.occasion_id ?? "");
  const [note, setNote] = useState(log.note ?? "");
  const [error, setError] = useState<string | null>(null);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setError(null);
        setDay(log.worn_on);
        setOccasion(log.occasion_id ?? "");
        setNote(log.note ?? "");
      }}
    >
      <DialogTrigger asChild>
        <Button variant="secondary" className="px-3">
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit this wear</DialogTitle>
          <DialogDescription>
            Change the day, the occasion, or the note.
          </DialogDescription>
        </DialogHeader>
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={async (event) => {
            event.preventDefault();
            setError(null);
            try {
              await update.mutateAsync({
                worn_on: day,
                occasion_id: occasion || null,
                note: note.trim() || null,
              });
              setOpen(false);
              toast.success("Wear log saved");
            } catch (failure) {
              setError(problemFrom(failure).message);
            }
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
          <Field label="Occasion (optional)">
            {(control) => (
              <Select
                value={occasion}
                onChange={(event) => setOccasion(event.target.value)}
                {...control}
              >
                <option value="">None</option>
                {reference.occasions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label="Note (optional)">
            {(control) => (
              <Textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                maxLength={500}
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
            <Button type="submit" loading={update.isPending}>
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function DeleteEntry({ log, title }: { log: WearLog; title: string }) {
  const remove = useDeleteWearLog(log.id);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setError(null);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="quiet" className="px-3">
          Delete
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete this wear?</DialogTitle>
          <DialogDescription>
            {`${title}, ${dayPhrase(log.worn_on)}.`} Wear counts go down by one
            for each piece.
          </DialogDescription>
        </DialogHeader>
        {error && <Alert tone="error">{error}</Alert>}
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            loading={remove.isPending}
            onClick={async () => {
              setError(null);
              try {
                await remove.mutateAsync();
                setOpen(false);
                toast.success("Wear deleted");
              } catch (failure) {
                setError(problemFrom(failure).message);
              }
            }}
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
