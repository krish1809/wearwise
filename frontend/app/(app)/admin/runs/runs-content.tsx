"use client";

import Link from "next/link";
import { useState } from "react";

import { PageLoading } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  type AgentRun,
  type RunKind,
  stoppedBecause,
  useRuns,
} from "@/lib/admin";
import { focusRing } from "@/lib/utils";

const STATUS: Record<string, string> = {
  done: "Done",
  stopped: "Stopped early",
  failed: "Failed",
  running: "Running",
};

const KINDS: { kind: RunKind; label: string; about: string }[] = [
  {
    kind: "trend_scout",
    label: "Trend Scout",
    about:
      "Every run, newest first: what it searched for, read, kept, and dropped, and what it cost.",
  },
  {
    kind: "weekly_digest",
    label: "Weekly email",
    about:
      "Every run, newest first: how many emails were due, sent, held back, or failed, and what the wording cost. Counts only: never who.",
  },
];

export function RunsContent() {
  const [kind, setKind] = useState<RunKind>("trend_scout");
  const runs = useRuns(kind);
  const shown = KINDS.find((k) => k.kind === kind) ?? KINDS[0];

  if (runs.isError) {
    return (
      <ErrorState
        title="Couldn't load the runs"
        action={
          <Button variant="secondary" onClick={() => void runs.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (runs.data === null) {
    return (
      <EmptyState title="Page not found">
        There&apos;s nothing at this address.
      </EmptyState>
    );
  }

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Agent runs
        </h1>
        <p className="mt-1 text-ink-soft">
          {shown.about}{" "}
          <Link
            href="/admin/trends"
            className={`underline underline-offset-2 ${focusRing}`}
          >
            Trends to review
          </Link>
        </p>
      </div>

      <Tabs value={kind} onValueChange={(v) => setKind(v as RunKind)}>
        <TabsList aria-label="Which agent">
          {KINDS.map((k) => (
            <TabsTrigger key={k.kind} value={k.kind}>
              {k.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {runs.data === undefined ? (
        <PageLoading />
      ) : runs.data.runs.length === 0 ? (
        <p className="text-ink-soft">
          No runs yet. It runs from GitHub Actions, on its schedule or by hand.
        </p>
      ) : (
        <>
          {kind === "trend_scout" && (
            <p className="text-sm tabular-nums">
              {runs.data.credits_this_month} of {runs.data.credit_cap} search
              credits used this month.
            </p>
          )}
          <ul className="flex flex-col gap-4">
            {runs.data.runs.map((run) => (
              <li key={run.id}>
                <RunCard run={run} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

// What each count in a weekly email run means.
const SENT_COUNTS: [string, string][] = [
  ["due", "due"],
  ["sent", "sent"],
  ["wording_model", "sent in the model's words"],
  ["wording_template", "sent in the template's words"],
  ["held_by_allowlist", "held: not on the allowlist"],
  ["held_by_daily_cap", "held: the day's email limit"],
  ["failed", "failed"],
  ["nothing", "nothing worth buying"],
  ["over_cap", "left for the next run"],
];

function EmailCounts({ run }: { run: AgentRun }) {
  const counts = step(run, "send");
  const shown = SENT_COUNTS.filter(([key]) => number(counts[key]) > 0);
  if (shown.length === 0) {
    return <p className="mt-3 text-sm">Nobody was due.</p>;
  }
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm tabular-nums">
      {shown.map(([key, label]) => (
        <li key={key}>
          {number(counts[key])} {label}
        </li>
      ))}
    </ul>
  );
}

type Step = Record<string, unknown>;

function step(run: AgentRun, name: string): Step {
  const found = run.steps[name];
  return found && typeof found === "object" ? (found as Step) : {};
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((v): v is string => typeof v === "string")
    : [];
}

function number(value: unknown): number {
  return typeof value === "number" ? value : 0;
}

function RunCard({ run }: { run: AgentRun }) {
  const plan = step(run, "plan_queries");
  const read = step(run, "read");
  const search = step(run, "search");
  const validate = step(run, "validate");
  const saved = step(run, "save");
  const merging = step(run, "dedupe_merge");
  const queries = strings(plan.queries);
  const skipped = Object.entries(
    (read.skipped as Record<string, number> | undefined) ?? {},
  ).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const dropped = Array.isArray(validate.dropped)
    ? (validate.dropped as { name: string; reason: string }[])
    : [];
  const added = strings(saved.added);
  const again = strings(saved.merged);
  const seconds = run.finished_at
    ? Math.round(
        (new Date(run.finished_at).getTime() -
          new Date(run.started_at).getTime()) /
          1000,
      )
    : null;
  const cost = run.cost_micro_usd / 1_000_000;
  const facts = [
    run.trigger === "schedule" ? "On its schedule" : "Started by hand",
    seconds === null ? null : `${seconds} s`,
    `${run.search_credits} search credits`,
    `${(run.tokens_in + run.tokens_out).toLocaleString("en-IN")} tokens`,
    // Without the model's prices in the settings there's no cost to give.
    cost > 0 ? `about $${cost.toFixed(4)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <CardTitle>
          {new Date(run.started_at).toLocaleString("en-IN", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </CardTitle>
        <span className="rounded-full bg-tile px-3 py-0.5 text-sm font-medium">
          {STATUS[run.status] ?? run.status}
        </span>
      </div>
      <p className="mt-1 text-sm text-ink-soft tabular-nums">{facts}</p>
      {run.stopped_by && (
        <p className="mt-2 text-sm">
          {`Stopped early: ${stoppedBecause(run.stopped_by)}.`}
        </p>
      )}
      {run.errors.length > 0 && (
        <ul className="mt-2 flex flex-col gap-1 text-sm">
          {run.errors.map((error) => (
            <li key={error} className="break-words">
              {error}
            </li>
          ))}
        </ul>
      )}
      {run.steps.resumed === true && (
        <p className="mt-2 text-sm">
          Carried on from a run that failed part-way.
        </p>
      )}

      {run.kind === "weekly_digest" && <EmailCounts run={run} />}

      {run.kind === "trend_scout" && (
        <details className="mt-3 text-sm">
          <summary className={`cursor-pointer font-medium ${focusRing}`}>
            What it did
          </summary>
          <div className="mt-3 flex flex-col gap-3">
            {queries.length > 0 && (
              <div>
                <h3 className="font-medium">
                  Searched for
                  {plan.planned_by === "template" && " (from templates)"}
                </h3>
                <ul className="mt-1 list-disc pl-5">
                  {queries.map((query) => (
                    <li key={query}>{query}</li>
                  ))}
                </ul>
              </div>
            )}
            {Object.keys(search).length > 0 && (
              <p>
                Read {number(read.read)} pages from {number(search.searched)}{" "}
                searches
                {number(search.failed) > 0 &&
                  ` (${number(search.failed)} failed)`}
                {skipped.length > 0 &&
                  `. Not read: ${skipped.map(([why, n]) => `${why} (${n})`).join(", ")}`}
                .
              </p>
            )}
            {(added.length > 0 || again.length > 0 || dropped.length > 0) && (
              <div>
                <h3 className="font-medium">What it found</h3>
                <ul className="mt-1 list-disc pl-5">
                  {added.length > 0 && <li>New: {added.join(", ")}</li>}
                  {again.length > 0 && <li>Found again: {again.join(", ")}</li>}
                  {dropped.map((d) => (
                    <li key={`${d.name}-${d.reason}`}>
                      Dropped {d.name}: {d.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {number(merging.expired) > 0 && (
              <p>
                {number(merging.expired)} trends expired, unseen for 8 weeks.
              </p>
            )}
          </div>
        </details>
      )}
    </Card>
  );
}
