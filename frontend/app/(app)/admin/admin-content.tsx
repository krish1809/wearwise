"use client";

import Link from "next/link";

import { PageLoading } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { type Stats, useStats } from "@/lib/admin";
import { percent } from "@/lib/insights";
import { focusRing } from "@/lib/utils";

export function AdminContent() {
  const stats = useStats();
  if (stats.isError) {
    return (
      <ErrorState
        title="Couldn't load the counts"
        action={
          <Button variant="secondary" onClick={() => void stats.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (stats.data === undefined) return <PageLoading />;
  if (stats.data === null) {
    return (
      <EmptyState title="Page not found">
        There&apos;s nothing at this address.
      </EmptyState>
    );
  }
  return <Counts stats={stats.data} />;
}

function Counts({ stats }: { stats: Stats }) {
  const tiles = [
    {
      label: "People",
      value: stats.users,
      note: `${stats.new_users_7d} this week`,
    },
    { label: "Demo accounts", value: stats.demo_users },
    { label: "Items", value: stats.items },
    { label: "Photos", value: stats.photos },
    { label: "Outfits", value: stats.outfits },
    {
      label: "Days of wear logged",
      value: stats.wear_logs,
      note: `${stats.wear_logs_7d} this week`,
    },
  ];
  return (
    <div className="flex max-w-5xl flex-col gap-8">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Counts
        </h1>
        <p className="mt-1 text-ink-soft">
          Straight from the database. Only the accounts in ADMIN_EMAILS see this
          page.
        </p>
        <nav
          aria-label="The owner's pages"
          className="mt-3 flex flex-wrap gap-x-5 gap-y-1"
        >
          <Link
            href="/admin/trends"
            className={`underline underline-offset-2 ${focusRing}`}
          >
            Trends to review
          </Link>
          <Link
            href="/admin/runs"
            className={`underline underline-offset-2 ${focusRing}`}
          >
            Agent runs
          </Link>
        </nav>
      </div>

      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {tiles.map((tile) => (
          <div key={tile.label} className="rounded-xl bg-surface p-4">
            <dt className="text-sm text-ink-soft">{tile.label}</dt>
            <dd className="mt-1 font-display text-2xl font-semibold tabular-nums">
              {tile.value}
            </dd>
            {tile.note && (
              <dd className="text-sm text-ink-soft tabular-nums">
                {tile.note}
              </dd>
            )}
          </div>
        ))}
      </dl>

      <Card>
        <CardTitle>Suggestions, last 30 days</CardTitle>
        <CardDescription className="mt-1">
          Accepted: liked, saved, or worn, each suggestion counted once.
        </CardDescription>
        {stats.acceptance.length === 0 ? (
          <p className="mt-3 text-sm text-ink-soft">None shown yet.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[28rem] text-sm tabular-nums">
              <thead className="text-left text-ink-soft">
                <tr>
                  <th scope="col" className="py-2 font-medium">
                    Engine
                  </th>
                  {["Shown", "Liked", "Saved", "Worn", "Accepted"].map(
                    (name) => (
                      <th
                        key={name}
                        scope="col"
                        className="py-2 text-right font-medium"
                      >
                        {name}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {stats.acceptance.map((row) => (
                  <tr key={row.engine_version} className="border-t border-line">
                    <th scope="row" className="py-2 text-left font-normal">
                      {row.engine_version}
                    </th>
                    <td className="py-2 text-right">{row.shown}</td>
                    <td className="py-2 text-right">{row.liked}</td>
                    <td className="py-2 text-right">{row.saved}</td>
                    <td className="py-2 text-right">{row.worn}</td>
                    <td className="py-2 text-right">
                      {row.accepted} (
                      {row.shown ? percent(row.accepted / row.shown) : "–"})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <CardTitle>Stylist today</CardTitle>
        <p className="mt-3 tabular-nums">
          {stats.ai_messages_today} messages, {stats.ai_images_today} photos
          read, ${stats.ai_spend_today_usd.toFixed(4)} of the $
          {stats.ai_daily_cap_usd.toFixed(2)} daily cap
        </p>
      </Card>

      <Card>
        <CardTitle>Errors</CardTitle>
        <CardDescription className="mt-1 tabular-nums">
          Last 24 hours: {stats.errors_24h.server ?? 0} on the server,{" "}
          {stats.errors_24h.browser ?? 0} in browsers. Kept 30 days.
        </CardDescription>
        {stats.recent_errors.length === 0 ? (
          <p className="mt-3 text-sm text-ink-soft">None recorded.</p>
        ) : (
          <ul className="mt-3 flex flex-col divide-y divide-line">
            {stats.recent_errors.map((error) => (
              <li key={error.id} className="flex flex-col gap-0.5 py-3 text-sm">
                <span className="text-ink-soft">
                  {new Date(error.created_at).toLocaleString("en-IN")} ·{" "}
                  {error.source} · {error.method ? `${error.method} ` : ""}
                  {error.path}
                  {error.request_id && ` · ref ${error.request_id}`}
                </span>
                <span className="break-words">
                  <span className="font-medium">{error.kind}:</span>{" "}
                  {error.message}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
