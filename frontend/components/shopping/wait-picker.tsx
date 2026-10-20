"use client";

import { Clock } from "lucide-react";
import { useId } from "react";

import { Button } from "@/components/ui/button";
import { FilterChip } from "@/components/ui/chip";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { dayLabel, dayPhrase, isoDay } from "@/lib/dates";
import { type Candidate, useUpdateCandidate } from "@/lib/shopping";

const WAITS = [
  { days: 7, label: "1 week" },
  { days: 14, label: "2 weeks" },
  { days: 30, label: "1 month" },
];

// Statuses where it's still wanted, so waiting makes sense.
export const WAITING = ["considering", "buy_next", "later"];

function inDays(days: number, now: Date = new Date()): string {
  const day = new Date(now);
  day.setDate(now.getDate() + days);
  return isoDay(day);
}

/**
 * Sleep on it: set a day to be asked again whether it's still wanted. The question shows
 * on the shopping list on that day.
 */
export function WaitPicker({ candidate }: { candidate: Candidate }) {
  const update = useUpdateCandidate(candidate.id);
  const labelId = useId();

  async function remind(day: string | null) {
    try {
      await update.mutateAsync({ remind_on: day });
      toast.success(
        day ? `We'll ask again ${dayPhrase(day)}.` : "Stopped waiting.",
      );
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  if (candidate.reminder_due) return <StillWant candidate={candidate} />;
  if (candidate.remind_on) {
    return (
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <p className="flex items-center gap-2 text-ink-soft">
          <Clock aria-hidden className="size-4" />
          Sleeping on it: we&apos;ll ask if you still want it{" "}
          {dayPhrase(candidate.remind_on)}.
        </p>
        <Button
          variant="quiet"
          loading={update.isPending}
          onClick={() => void remind(null)}
        >
          Stop waiting
        </Button>
      </div>
    );
  }
  return (
    <div
      role="group"
      aria-labelledby={labelId}
      className="flex flex-wrap items-center gap-2"
    >
      <span id={labelId} className="text-sm text-ink-soft">
        Not sure? Ask me again in
      </span>
      {WAITS.map((wait) => (
        <FilterChip
          key={wait.days}
          selected={false}
          disabled={update.isPending}
          onClick={() => void remind(inDays(wait.days))}
        >
          {wait.label}
        </FilterChip>
      ))}
    </div>
  );
}

/** The day has come: keep it on the list, or skip it (with an undo). */
export function StillWant({ candidate }: { candidate: Candidate }) {
  const update = useUpdateCandidate(candidate.id);

  async function keep() {
    try {
      await update.mutateAsync({ remind_on: null });
      toast.success("Kept on your list.");
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  async function skip() {
    // Undo puts it back on the list; the reminder day has passed, so it isn't set again.
    const before = { status: candidate.status };
    try {
      await update.mutateAsync({ status: "skipped" });
      toast.success("Skipped", {
        action: {
          label: "Undo",
          onClick: () =>
            void update
              .mutateAsync(before)
              .catch((error) => toast.error(problemFrom(error).message)),
        },
      });
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <p className="text-sm">
        You wanted to think it over until{" "}
        {candidate.remind_on ? dayLabel(candidate.remind_on) : "today"}. Still
        want it?
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          disabled={update.isPending}
          onClick={() => void keep()}
        >
          Yes, keep it
        </Button>
        <Button
          variant="quiet"
          disabled={update.isPending}
          onClick={() => void skip()}
        >
          Skip it
        </Button>
      </div>
    </div>
  );
}
