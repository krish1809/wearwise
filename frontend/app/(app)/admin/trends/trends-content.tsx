"use client";

import Link from "next/link";
import { useState } from "react";

import { PageLoading } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Swatch } from "@/components/ui/swatch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";
import {
  type AgentTrend,
  type TrendDecision,
  type TrendStatus,
  useDecideTrend,
  useTrends,
} from "@/lib/admin";
import { problemFrom } from "@/lib/api/errors";
import { focusRing } from "@/lib/utils";

const TABS: { status: TrendStatus; label: string; empty: string }[] = [
  {
    status: "pending",
    label: "Waiting",
    empty:
      "Nothing waiting. New trends appear here after each Trend Scout run.",
  },
  {
    status: "approved",
    label: "Approved",
    empty: "No approved trends yet: weekly emails have nothing to use.",
  },
  { status: "rejected", label: "Rejected", empty: "Nothing rejected." },
  {
    status: "expired",
    label: "Expired",
    empty: "Nothing has expired. A trend not seen for 8 weeks expires.",
  },
];

// What each status can be changed to, and the button's words.
const ACTIONS: Record<TrendStatus, { to: TrendDecision; label: string }[]> = {
  pending: [
    { to: "approved", label: "Approve" },
    { to: "rejected", label: "Reject" },
  ],
  approved: [
    { to: "rejected", label: "Reject" },
    { to: "pending", label: "Back to waiting" },
  ],
  rejected: [
    { to: "approved", label: "Approve" },
    { to: "pending", label: "Back to waiting" },
  ],
  expired: [],
};

const DONE: Record<TrendDecision, string> = {
  approved: "Approved: weekly emails can use it now.",
  rejected: "Rejected: no one will see it.",
  pending: "Back to waiting.",
};

export function TrendsContent() {
  const [status, setStatus] = useState<TrendStatus>("pending");
  const trends = useTrends(status);

  if (trends.isError) {
    return (
      <ErrorState
        title="Couldn't load the trends"
        action={
          <Button variant="secondary" onClick={() => void trends.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (trends.data === null) {
    return (
      <EmptyState title="Page not found">
        There&apos;s nothing at this address.
      </EmptyState>
    );
  }

  const tab = TABS.find((t) => t.status === status) ?? TABS[0];
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Trends
        </h1>
        <p className="mt-1 text-ink-soft">
          What the Trend Scout found on the web, each with its sources. Only
          approved trends reach anyone&apos;s weekly email.{" "}
          <Link
            href="/admin/runs"
            className={`underline underline-offset-2 ${focusRing}`}
          >
            How each run went
          </Link>
        </p>
      </div>

      <Tabs value={status} onValueChange={(v) => setStatus(v as TrendStatus)}>
        <TabsList aria-label="Trends by status">
          {TABS.map((t) => (
            <TabsTrigger key={t.status} value={t.status}>
              {t.label}
              {trends.data ? ` (${trends.data.counts[t.status] ?? 0})` : ""}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {trends.data === undefined ? (
        <PageLoading />
      ) : trends.data.trends.length === 0 ? (
        <p className="text-ink-soft">{tab.empty}</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {trends.data.trends.map((trend) => (
            <li key={trend.id}>
              <TrendCard trend={trend} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TrendCard({ trend }: { trend: AgentTrend }) {
  const decide = useDecideTrend();
  const status = trend.status as TrendStatus;
  const facts: { label: string; values: string[] }[] = [
    { label: "Pieces", values: trend.categories.map((c) => c.name) },
    { label: "Fabrics", values: trend.fabrics.map((f) => f.name) },
    { label: "Patterns", values: trend.patterns.map((p) => p.name) },
    { label: "Fits", values: trend.fits.map((f) => f.name) },
    { label: "Seasons", values: trend.seasons.map((s) => s.name) },
    { label: "Sections", values: trend.sections.map((s) => s.name) },
    { label: "Styles", values: trend.styles.map((s) => s.name) },
  ].filter((fact) => fact.values.length > 0);

  function change(to: TrendDecision) {
    decide.mutate(
      { id: trend.id, status: to },
      {
        onSuccess: () => toast.success(`${trend.name}. ${DONE[to]}`),
        onError: (error) => toast.error(problemFrom(error).message),
      },
    );
  }

  return (
    <Card>
      <CardTitle>{trend.name}</CardTitle>
      <p className="mt-2">{trend.summary}</p>
      <p className="mt-1 text-sm text-ink-soft">Why now: {trend.why_now}</p>

      <dl className="mt-4 grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-[8rem_1fr]">
        {trend.colors.length > 0 && (
          <>
            <dt className="text-ink-soft">Colours</dt>
            <dd className="flex flex-wrap gap-x-3 gap-y-1">
              {trend.colors.map((colour) => (
                <span
                  key={colour.id}
                  className="inline-flex items-center gap-1.5"
                >
                  <Swatch hex={colour.hex} />
                  {colour.name}
                </span>
              ))}
            </dd>
          </>
        )}
        {facts.map((fact) => (
          <div key={fact.label} className="contents">
            <dt className="text-ink-soft">{fact.label}</dt>
            <dd>{fact.values.join(", ")}</dd>
          </div>
        ))}
      </dl>

      <h3 className="mt-5 text-sm font-medium">
        Sources ({trend.sources.length})
      </h3>
      <ul className="mt-2 flex flex-col gap-3">
        {trend.sources.map((source) => (
          <li key={source.url} className="text-sm">
            <span className="text-ink-soft">
              {source.domain} · {shortDate(source.published_on)}
            </span>
            <br />
            {isWebAddress(source.url) ? (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`break-words underline underline-offset-2 ${focusRing}`}
              >
                {source.title}
              </a>
            ) : (
              <span className="break-words">{source.title}</span>
            )}
            <blockquote className="mt-1 border-l-2 border-line pl-3 text-ink-soft">
              &ldquo;{source.quote}&rdquo;
            </blockquote>
          </li>
        ))}
      </ul>

      <p className="mt-4 text-sm text-ink-soft">
        First found {shortDate(trend.first_seen_at)}, last seen{" "}
        {shortDate(trend.last_seen_at)}.
      </p>
      {ACTIONS[status].length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {ACTIONS[status].map((action, n) => (
            <Button
              key={action.to}
              variant={n === 0 ? "primary" : "secondary"}
              disabled={decide.isPending}
              onClick={() => change(action.to)}
            >
              {action.label}
            </Button>
          ))}
        </div>
      )}
    </Card>
  );
}

function shortDate(value: string): string {
  const date =
    value.length === 10 ? new Date(`${value}T00:00:00`) : new Date(value);
  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Sources are web pages; anything else isn't made a link. */
function isWebAddress(url: string): boolean {
  return url.startsWith("https://") || url.startsWith("http://");
}
