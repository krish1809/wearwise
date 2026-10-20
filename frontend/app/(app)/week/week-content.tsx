"use client";

import { CalendarPlus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { DayCard } from "@/components/week/day-card";
import { EventDialog, UsualWeekDialog } from "@/components/week/week-dialogs";
import { problemFrom } from "@/lib/api/errors";
import { dayLabel, todayIso } from "@/lib/dates";
import {
  useDeleteEvent,
  useEvents,
  usePlanWeek,
  useWeek,
  weekdayOf,
} from "@/lib/plan";
import type { Profile, Reference } from "@/lib/profile";

export function WeekContent() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          My Week
        </h1>
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="secondary">
            <Link href="/laundry">Laundry</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/trips">Trips</Link>
          </Button>
        </div>
      </div>
      <WardrobeData>
        {({ reference, profile }) => (
          <Planner reference={reference} profile={profile} />
        )}
      </WardrobeData>
    </div>
  );
}

function Planner({
  reference,
  profile,
}: {
  reference: Reference;
  profile: Profile;
}) {
  // Logged-in pages only render in the browser (D32), so the browser's own today is safe.
  const [start] = useState(todayIso);
  const week = useWeek(start);
  const planWeek = usePlanWeek(start);
  const [usualOpen, setUsualOpen] = useState(false);
  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const occasionNames = new Map(reference.occasions.map((o) => [o.id, o.name]));

  async function plan() {
    try {
      await planWeek.mutateAsync();
      toast.success("Week planned");
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  if (week.isError) {
    return (
      <ErrorState
        title="Couldn't load your week"
        action={
          <Button variant="secondary" onClick={() => void week.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!week.data) {
    return (
      <div
        aria-busy="true"
        className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3"
      >
        {[0, 1, 2].map((key) => (
          <Skeleton key={key} className="h-96" />
        ))}
        <span role="status" className="sr-only">
          Loading your week
        </span>
      </div>
    );
  }

  const days = week.data.days;
  const planned = days.some(
    (day) => day.pieces.length > 0 || day.missing.length > 0,
  );
  const noOccasions = days.every((day) => day.occasion_source === "none");

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap gap-3">
        <Button loading={planWeek.isPending} onClick={() => void plan()}>
          {planned ? "Plan again" : "Plan my week"}
        </Button>
        <UsualWeekDialog
          profile={profile}
          reference={reference}
          open={usualOpen}
          onOpenChange={setUsualOpen}
          trigger={<Button variant="secondary">Your usual week</Button>}
        />
        <EventDialog
          reference={reference}
          trigger={
            <Button variant="secondary">
              <CalendarPlus aria-hidden />
              Add an event
            </Button>
          }
        />
      </div>
      {planned && (
        <p className="text-sm text-ink-soft">
          Planning again keeps locked days and days you&apos;ve worn.
        </p>
      )}
      {noOccasions && (
        <Alert>
          Set your usual week first, so each day has an occasion to dress for.{" "}
          <button
            type="button"
            className="font-medium text-indigo underline underline-offset-4"
            onClick={() => setUsualOpen(true)}
          >
            Set your usual week
          </button>
        </Alert>
      )}
      <ol className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {days.map((day) => {
          const usual = profile.weekday_occasions[String(weekdayOf(day.day))];
          return (
            <li key={day.day}>
              <DayCard
                day={day}
                start={start}
                reference={reference}
                usualName={
                  usual
                    ? (occasionNames.get(usual) ?? null)
                    : profile.occasion_ids[0]
                      ? (occasionNames.get(profile.occasion_ids[0]) ?? null)
                      : null
                }
                slots={slots}
                familyHex={familyHex}
              />
            </li>
          );
        })}
      </ol>
      <Events occasionNames={occasionNames} />
    </div>
  );
}

function Events({ occasionNames }: { occasionNames: Map<string, string> }) {
  const events = useEvents();
  const remove = useDeleteEvent();
  if (!events.data || events.data.length === 0) return null;
  return (
    <section aria-labelledby="events-heading" className="flex flex-col gap-3">
      <h2 id="events-heading" className="text-lg font-medium">
        Coming up
      </h2>
      <ul className="flex flex-col gap-2">
        {events.data.map((event) => (
          <li
            key={event.id}
            className="flex items-center justify-between gap-3 rounded-lg bg-surface px-4 py-2"
          >
            <span className="min-w-0">
              <span className="block font-medium">{event.title}</span>
              <span className="block text-sm text-ink-soft">
                {dayLabel(event.day)} ·{" "}
                {occasionNames.get(event.occasion_id) ?? event.occasion_id}
              </span>
            </span>
            <Button
              variant="quiet"
              className="px-3"
              aria-label={`Delete ${event.title}`}
              loading={remove.isPending && remove.variables === event.id}
              onClick={async () => {
                try {
                  await remove.mutateAsync(event.id);
                  toast.success("Event deleted");
                } catch (error) {
                  toast.error(problemFrom(error).message);
                }
              }}
            >
              <Trash2 aria-hidden />
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
