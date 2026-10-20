"use client";

import { Flag } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
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
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { problemFrom } from "@/lib/api/errors";
import { dayLabel } from "@/lib/dates";
import {
  type Challenge,
  useChallenge,
  useStartChallenge,
  useStopChallenge,
} from "@/lib/insights";
import { cn, focusRing } from "@/lib/utils";

type Running = NonNullable<Challenge["challenge"]>;

/** "today", "yesterday", or "Mon 12 Oct", for after "since". */
function since(iso: string): string {
  const label = dayLabel(iso);
  return label === "Today" || label === "Yesterday"
    ? label.toLowerCase()
    : label;
}

/**
 * Wear what you own: try to wear every piece at least once in 60 days. Progress is counted
 * from the wear log, nothing else.
 */
export function ChallengeCard({
  familyHex,
}: {
  familyHex: Map<string, string | null>;
}) {
  const challenge = useChallenge();
  const start = useStartChallenge();

  async function begin() {
    try {
      await start.mutateAsync();
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  if (challenge.isError) return null;
  if (!challenge.data) return <Skeleton className="h-36" />;
  const running = challenge.data.challenge;

  return (
    <Card>
      <div className="flex items-start gap-3">
        <Flag aria-hidden className="mt-0.5 size-5 shrink-0 text-indigo" />
        <div className="min-w-0 flex-1">
          <CardTitle>Wear what you own</CardTitle>
          {!running ? (
            <>
              <CardDescription className="mt-1">
                For {challenge.data.days} days, try to wear every piece you own
                at least once. Progress comes from what you log as worn.
              </CardDescription>
              <Button
                className="mt-4"
                loading={start.isPending}
                onClick={() => void begin()}
              >
                Start the challenge
              </Button>
            </>
          ) : (
            <Progress
              running={running}
              familyHex={familyHex}
              onRestart={() => void begin()}
              restarting={start.isPending}
            />
          )}
        </div>
      </div>
    </Card>
  );
}

function Progress({
  running,
  familyHex,
  onRestart,
  restarting,
}: {
  running: Running;
  familyHex: Map<string, string | null>;
  onRestart: () => void;
  restarting: boolean;
}) {
  const share = running.total ? running.worn / running.total : 0;
  const more = running.unworn_count - running.unworn.length;

  return (
    <div className="mt-1 flex flex-col gap-4">
      <p className="text-sm text-ink-soft">
        {running.finished
          ? `Finished ${dayLabel(running.ends_on)}. You wore ${running.worn} of ${running.total} pieces in ${running.days} days.`
          : `Day ${running.day} of ${running.days} · ends ${dayLabel(running.ends_on)}`}
      </p>
      <div className="flex flex-col gap-1.5">
        <div
          role="progressbar"
          aria-label="Pieces worn"
          aria-valuemin={0}
          aria-valuemax={running.total}
          aria-valuenow={running.worn}
          aria-valuetext={`${running.worn} of ${running.total}`}
          className="h-2 overflow-hidden rounded-full bg-tile"
        >
          <div
            className="h-full rounded-full bg-indigo motion-safe:transition-[width]"
            style={{ width: `${Math.round(share * 100)}%` }}
          />
        </div>
        <p className="text-sm tabular-nums">
          {running.worn} of {running.total} pieces worn since{" "}
          {since(running.started_on)}
        </p>
      </div>
      {running.unworn_count === 0 ? (
        <p className="font-medium">Every piece has been worn. Well done.</p>
      ) : (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-medium">
            {running.finished ? "Never worn in the challenge" : "Not worn yet"}
          </h3>
          <ul className="flex flex-wrap gap-2">
            {running.unworn.map((item) => (
              <li key={item.id}>
                <Link
                  href={`/wardrobe/${item.id}`}
                  title={item.display_name}
                  aria-label={item.display_name}
                  className={cn(
                    "flex size-14 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full",
                    focusRing,
                  )}
                >
                  <ItemPhoto
                    photo={item.photo}
                    alt=""
                    hex={item.color_hex ?? familyHex.get(item.color_primary)}
                  />
                </Link>
              </li>
            ))}
          </ul>
          {more > 0 && <p className="text-sm text-ink-soft">and {more} more</p>}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {running.finished ? (
          <Button variant="secondary" loading={restarting} onClick={onRestart}>
            Start again
          </Button>
        ) : (
          <Button asChild variant="secondary">
            <Link href="/worn/new">Log what I wore</Link>
          </Button>
        )}
        <StopDialog finished={running.finished} />
      </div>
    </div>
  );
}

function StopDialog({ finished }: { finished: boolean }) {
  const stop = useStopChallenge();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setError(null);
    try {
      await stop.mutateAsync();
      setOpen(false);
    } catch (failure) {
      setError(problemFrom(failure).message);
    }
  }

  if (finished) {
    return (
      <Button
        variant="quiet"
        loading={stop.isPending}
        onClick={() => void confirm()}
      >
        Close it
      </Button>
    );
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="quiet">Stop</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Stop the challenge?</DialogTitle>
          <DialogDescription>
            Your wear log stays as it is; only the challenge ends. You can start
            a new one any time.
          </DialogDescription>
        </DialogHeader>
        {error && <Alert tone="error">{error}</Alert>}
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Keep going</Button>
          </DialogClose>
          <Button loading={stop.isPending} onClick={() => void confirm()}>
            Stop
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
