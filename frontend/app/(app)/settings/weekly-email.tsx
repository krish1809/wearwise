"use client";

import Link from "next/link";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import {
  type DigestSettings,
  useChangeDigestSettings,
  useDigestSettings,
  WEEKDAYS,
} from "@/lib/digests";
import { focusRing } from "@/lib/utils";

/** The weekly email: off until turned on and the address confirmed (docs/AGENTS.md). */
export function WeeklyEmail({ isDemo }: { isDemo: boolean }) {
  const settings = useDigestSettings();
  return (
    <Card id="email">
      <CardTitle>Weekly email</CardTitle>
      <CardDescription className="mt-1">
        Once a week, up to three picks worth a look, from what&apos;s in fashion
        and what you already own, with where to find them. Off until you turn it
        on.{" "}
        <Link
          href="/picks"
          className={`underline underline-offset-2 ${focusRing}`}
        >
          See this week&apos;s picks
        </Link>
      </CardDescription>
      <div className="mt-4">
        {isDemo ? (
          <p className="text-sm">
            A demo account can&apos;t get email. Make your own account to turn
            it on.
          </p>
        ) : settings.data === undefined ? (
          settings.isError ? (
            <p className="text-sm">Couldn&apos;t load this. Try again later.</p>
          ) : (
            <Skeleton className="h-11 w-48" />
          )
        ) : (
          <Controls found={settings.data} />
        )}
      </div>
    </Card>
  );
}

function Controls({ found }: { found: DigestSettings }) {
  const change = useChangeDigestSettings();
  const [weekday, setWeekday] = useState(found.weekday);
  const dayId = useId();

  function apply(
    next: Parameters<typeof change.mutate>[0],
    done?: (after: DigestSettings) => string,
  ) {
    change.mutate(next, {
      onSuccess: (after) => {
        if (done) toast.success(done(after));
      },
      onError: (error) => toast.error(problemFrom(error).message),
    });
  }

  if (found.preview_only) {
    return (
      <p className="text-sm">
        For now the weekly email goes only to WearWise&apos;s owner, while its
        email is being set up. Your picks are on the{" "}
        <Link
          href="/picks"
          className={`underline underline-offset-2 ${focusRing}`}
        >
          Weekly picks
        </Link>{" "}
        page.
      </p>
    );
  }

  const dayPicker = (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={dayId} className="text-sm font-medium">
        Day
      </label>
      <Select
        id={dayId}
        className="w-48"
        value={weekday}
        disabled={change.isPending}
        onChange={(event) => {
          const day = Number(event.target.value);
          setWeekday(day);
          if (found.on) {
            apply(
              { action: "day", weekday: day },
              () => `It'll come on ${WEEKDAYS[day]}s.`,
            );
          }
        }}
      >
        {WEEKDAYS.map((name, n) => (
          <option key={name} value={n}>
            {name}
          </option>
        ))}
      </Select>
    </div>
  );

  if (found.on) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm">
          On: every {WEEKDAYS[found.weekday]} morning, to{" "}
          <span className="break-all">{found.email}</span>.
        </p>
        {dayPicker}
        <div>
          <Button
            variant="secondary"
            disabled={change.isPending}
            onClick={() =>
              apply({ action: "off" }, () => "The weekly email is off.")
            }
          >
            Turn it off
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {found.waiting_for_confirmation && (
        <p role="status" className="text-sm">
          A link is on its way to{" "}
          <span className="break-all">{found.email}</span>. Follow it to turn
          the email on; it works for two days.
        </p>
      )}
      {dayPicker}
      <div>
        <Button
          disabled={change.isPending}
          onClick={() =>
            apply({ action: "on", weekday }, (after) =>
              after.on
                ? `On: every ${WEEKDAYS[after.weekday]}.`
                : "Check your email for the link to turn it on.",
            )
          }
        >
          {found.waiting_for_confirmation
            ? "Send the link again"
            : "Turn it on"}
        </Button>
      </div>
    </div>
  );
}
