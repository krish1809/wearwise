"use client";

import { ExternalLink } from "lucide-react";
import Link from "next/link";

import { PageLoading } from "@/components/app-shell";
import { OwnedRow } from "@/components/shopping/piece-row";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Swatch } from "@/components/ui/swatch";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import {
  type Digest,
  type DigestPick,
  useLatestDigest,
  useNotForMe,
  useWorkOutPicks,
} from "@/lib/digests";
import { formatRupees } from "@/lib/money";
import { useReference } from "@/lib/profile";
import { focusRing } from "@/lib/utils";

const ABOUT =
  "What's in fashion in India now, judged against what you already own. A trend becomes a pick only when it would add to your wardrobe, or when you already have it.";

export function PicksContent() {
  const digest = useLatestDigest();
  const workOut = useWorkOutPicks();

  function work() {
    workOut.mutate(undefined, {
      onError: (error) => toast.error(problemFrom(error).message),
    });
  }

  if (digest.isError) {
    return (
      <ErrorState
        title="Couldn't load your picks"
        action={
          <Button variant="secondary" onClick={() => void digest.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (digest.data === undefined) return <PageLoading />;

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Weekly picks
        </h1>
        <p className="mt-1 text-ink-soft">{ABOUT}</p>
      </div>
      {digest.data === null ? (
        <EmptyState
          title="No picks yet"
          action={
            <Button onClick={work} disabled={workOut.isPending}>
              {workOut.isPending
                ? "Working them out…"
                : "Show this week's picks"}
            </Button>
          }
        >
          Working them out takes a few seconds: each trend is checked against
          every outfit you can make.
        </EmptyState>
      ) : (
        <Picks
          digest={digest.data}
          onWorkOut={work}
          working={workOut.isPending}
        />
      )}
    </div>
  );
}

function Picks({
  digest,
  onWorkOut,
  working,
}: {
  digest: Digest;
  onWorkOut: () => void;
  working: boolean;
}) {
  const workedOut = new Date(digest.worked_out_at).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <>
      <div>
        <h2 className="text-lg font-medium">{digest.subject}</h2>
        <p className="mt-1 text-sm text-ink-soft">
          {digest.status === "sent" ? "Emailed" : "Worked out"} {workedOut}.
        </p>
        {digest.status !== "sent" && (
          <Button
            variant="secondary"
            className="mt-3"
            onClick={onWorkOut}
            disabled={working}
          >
            {working ? "Working them out…" : "Work them out again"}
          </Button>
        )}
      </div>
      {digest.note && <p className="text-ink-soft">{digest.note}</p>}
      {digest.note?.startsWith("Choose the occasions") && (
        <p>
          <Link
            href="/settings"
            className={`underline underline-offset-2 ${focusRing}`}
          >
            Choose your occasions
          </Link>
        </p>
      )}
      {digest.picks.length > 0 && (
        <ul className="flex flex-col gap-4">
          {digest.picks.map((pick) => (
            <li key={pick.id}>
              <PickCard pick={pick} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function PickCard({ pick }: { pick: DigestPick }) {
  const notForMe = useNotForMe();
  const reference = useReference();
  const familyHex = new Map(
    (reference.data?.color_families ?? []).map((c) => [c.id, c.hex]),
  );

  function answer(value: boolean) {
    notForMe.mutate(
      { id: pick.id, notForMe: value },
      {
        onSuccess: () => {
          if (value) {
            toast.success("Noted: picks like this come up less.", {
              action: { label: "Undo", onClick: () => answer(false) },
            });
          }
        },
        onError: (error) => toast.error(problemFrom(error).message),
      },
    );
  }

  const label =
    pick.kind === "owned"
      ? "Already yours"
      : pick.verdict === "buy"
        ? "Worth buying"
        : "Worth a look";

  return (
    <Card className={pick.not_for_me ? "opacity-70" : undefined}>
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <CardTitle className="flex items-center gap-2">
          <Swatch hex={pick.color_hex} />
          {pick.name}
        </CardTitle>
        <span className="rounded-full bg-tile px-3 py-0.5 text-sm font-medium">
          {label}
        </span>
      </div>
      <p className="mt-2 text-sm text-ink-soft">
        In fashion now: {pick.trend_name}. {pick.trend_summary}
      </p>
      <p className="mt-2">{pick.text}</p>

      {pick.reasons.length > 0 && (
        <ul className="mt-3 list-disc pl-5 text-sm">
          {pick.reasons.slice(0, 3).map((reason) => (
            <li key={reason.code}>{reason.text}</li>
          ))}
        </ul>
      )}

      {pick.items.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">
            {pick.kind === "owned"
              ? "Yours, and what to wear it with"
              : "Wear it with"}
          </h3>
          <ul className="mt-2 flex flex-col gap-2">
            {pick.items.map((item) => (
              <li key={item.id}>
                <OwnedRow item={item} familyHex={familyHex} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {pick.links.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">
            Look for it
            {pick.usual_spend !== null &&
              ` (you usually spend up to ${formatRupees(pick.usual_spend)})`}
          </h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {pick.links.map((link) => (
              <li key={link.shop_id}>
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`inline-flex h-11 items-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-sm hover:bg-tile ${focusRing}`}
                >
                  {link.shop}
                  <ExternalLink aria-hidden className="size-3.5" />
                  <span className="sr-only">(opens the shop&apos;s site)</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4">
        {pick.not_for_me ? (
          <p className="text-sm">
            Marked not for me.{" "}
            <button
              type="button"
              className={`underline underline-offset-2 ${focusRing}`}
              onClick={() => answer(false)}
              disabled={notForMe.isPending}
            >
              Undo
            </button>
          </p>
        ) : (
          <Button
            variant="quiet"
            onClick={() => answer(true)}
            disabled={notForMe.isPending}
          >
            Not for me
          </Button>
        )}
      </div>
    </Card>
  );
}
