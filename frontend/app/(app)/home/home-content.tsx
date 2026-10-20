"use client";

import { CloudSun } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageLoading } from "@/components/app-shell";
import { OutfitBoard } from "@/components/outfits/outfit-board";
import { TextLink } from "@/components/text-link";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { useCurrentUser } from "@/lib/auth";
import { todayIso } from "@/lib/dates";
import { useInsights } from "@/lib/insights";
import { formatRupees } from "@/lib/money";
import { useWearLogs } from "@/lib/outfits";
import { useWearDay, useWeek } from "@/lib/plan";
import { listed } from "@/lib/text";
import {
  useDismissOnboardingReminder,
  useProfile,
  useReference,
} from "@/lib/profile";
import { piecesName } from "@/lib/suggestions";
import { weatherLine } from "@/lib/weather";

export function HomeContent() {
  const { data: user } = useCurrentUser();
  if (!user) return <PageLoading />;
  const firstName = user.name?.split(/\s+/)[0];

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          {firstName ? `Hello, ${firstName}` : "Hello"}
        </h1>
        <p className="mt-3 max-w-prose text-ink-soft">
          You&apos;re logged in as {user.email}. Your profile, sizes, and
          account are in <TextLink href="/settings">Settings</TextLink>.
        </p>
      </div>
      <Today />
      <OneInsight />
      <FinishSetup />
    </div>
  );
}

/** One fact from Insights, a different one each day, with a link to the rest. */
function OneInsight() {
  const insights = useInsights();
  const reference = useReference();
  const [day] = useState(() => {
    const now = new Date();
    return Math.floor(
      (now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) /
        86_400_000,
    );
  });
  const data = insights.data;
  if (!data || !reference.data) return null;
  const occasions = new Map(
    reference.data.occasions.map((o) => [o.id, o.name]),
  );
  const seasons = new Map(reference.data.seasons.map((s) => [s.id, s.name]));
  const facts: string[] = [];
  const top = data.most_worn[0];
  if (top) {
    facts.push(
      `Your most worn piece is the ${lower(top.item.display_name)}: ${top.wears} times.`,
    );
  }
  const best = data.cheapest[0];
  if (best) {
    facts.push(
      `Best value so far: the ${lower(best.item.display_name)}, at ${formatRupees(best.per_wear)} a wear.`,
    );
  }
  const orphan = data.orphans?.[0];
  if (orphan) {
    facts.push(
      `The ${lower(orphan.item.display_name)} goes with little. ${orphan.rescue}`,
    );
  }
  const gap = data.coverage?.cells.find((cell) => cell.outfits === 0);
  if (gap) {
    facts.push(
      `No good outfit yet for ${lower(occasions.get(gap.occasion_id) ?? gap.occasion_id)} in ${lower(seasons.get(gap.season) ?? gap.season)}.`,
    );
  }
  if (data.needs_price.length > 0) {
    const count = data.needs_price.length;
    facts.push(
      `${count} worn ${count === 1 ? "piece has" : "pieces have"} no price, so there's no cost per wear yet.`,
    );
  }
  if (facts.length === 0) return null;
  return (
    <Card className="flex flex-col gap-3">
      <CardTitle>From your insights</CardTitle>
      <p className="max-w-prose">{facts[day % facts.length]}</p>
      <TextLink href="/insights" className="self-start">
        See all insights
      </TextLink>
    </Card>
  );
}

function lower(name: string): string {
  return /^[A-Z]{2}/.test(name)
    ? name
    : name.charAt(0).toLowerCase() + name.slice(1);
}

/** Shown once onboarding was skipped, until the person finishes it or says not now. */
function FinishSetup() {
  const { data: profile } = useProfile();
  const dismiss = useDismissOnboardingReminder();
  if (!profile?.show_onboarding_reminder) return null;

  return (
    <Card className="flex flex-col gap-4">
      <div>
        <CardTitle>Finish setting up WearWise</CardTitle>
        <CardDescription className="mt-1 max-w-prose">
          Your sizes, style, and budget help WearWise suggest what suits you.
          Every question is optional.
        </CardDescription>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link href="/onboarding">Finish setup</Link>
        </Button>
        <Button
          variant="quiet"
          loading={dismiss.isPending}
          onClick={() =>
            dismiss.mutate(undefined, {
              onError: (error) => toast.error(problemFrom(error).message),
            })
          }
        >
          Not now
        </Button>
      </div>
    </Card>
  );
}

/** Today's weather, and what was worn: or the outfit planned for today, or a nudge. */
function Today() {
  const [today] = useState(todayIso);
  const logs = useWearLogs({ on: today });
  const week = useWeek(today);
  const reference = useReference();
  const wear = useWearDay(today);
  if (!logs.data) return null;
  const worn = logs.data.pages.flatMap((page) => page.logs);
  const pieces = worn.flatMap((log) => log.pieces.map((piece) => piece.name));
  const plan = week.data?.days[0];
  const planned = plan && plan.pieces.length > 0 && !plan.worn ? plan : null;

  return (
    <Card className="flex flex-col gap-4">
      <div>
        <CardTitle>Today</CardTitle>
        {plan && (
          <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-soft">
            <CloudSun aria-hidden className="size-4 shrink-0" />
            {weatherLine(plan.weather)}
          </p>
        )}
        <CardDescription className="mt-1 max-w-prose">
          {worn.length > 0
            ? `You wore ${listed(pieces)}.`
            : planned
              ? `Planned: ${piecesName(planned.pieces)}.`
              : "Nothing logged for today yet. Logging what you wear keeps wear counts and laundry right."}
        </CardDescription>
      </div>
      {worn.length === 0 && planned && reference.data && (
        <div className="max-w-xs">
          <OutfitBoard
            pieces={planned.pieces.map((piece) => ({
              slot: piece.slot,
              name: piece.item.display_name,
              removed: false,
              item: piece.item,
            }))}
            slots={reference.data.slots.map((slot, position) => ({
              ...slot,
              position,
            }))}
            familyHex={
              new Map(reference.data.color_families.map((c) => [c.id, c.hex]))
            }
            size="small"
          />
        </div>
      )}
      <div className="flex flex-wrap gap-3">
        {worn.length > 0 ? (
          <Button asChild variant="secondary">
            <Link href="/worn">See the wear log</Link>
          </Button>
        ) : planned ? (
          <>
            <Button
              loading={wear.isPending}
              onClick={() =>
                wear.mutate(planned.day, {
                  onSuccess: () => toast.success("Marked as worn today"),
                  onError: (error) => toast.error(problemFrom(error).message),
                })
              }
            >
              I wore this
            </Button>
            <Button asChild variant="secondary">
              <Link href="/week">See my week</Link>
            </Button>
          </>
        ) : (
          <>
            <Button asChild>
              <Link href="/outfits/suggest">Suggest an outfit</Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/week">Plan my week</Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/worn/new">Log loose items</Link>
            </Button>
          </>
        )}
      </div>
    </Card>
  );
}
