"use client";

import { ChartColumn } from "lucide-react";
import Link from "next/link";
import { useId } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { dayPhrase } from "@/lib/dates";
import {
  type CostRow,
  type Insights,
  monthLabel,
  percent,
  useInsights,
  type WornRow,
} from "@/lib/insights";
import { formatRupees } from "@/lib/money";
import type { Reference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";

type Brief = WornRow["item"];

export function InsightsContent() {
  const insights = useInsights();
  return (
    <div className="flex max-w-5xl flex-col gap-8">
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Insights
      </h1>
      {insights.isError ? (
        <ErrorState
          title="Couldn't load your insights"
          action={
            <Button variant="secondary" onClick={() => void insights.refetch()}>
              Try again
            </Button>
          }
        >
          Check your connection and try again.
        </ErrorState>
      ) : !insights.data ? (
        <div aria-busy="true" className="grid gap-6 md:grid-cols-2">
          {[0, 1, 2, 3].map((key) => (
            <Skeleton key={key} className="h-56" />
          ))}
          <span role="status" className="sr-only">
            Loading your insights
          </span>
        </div>
      ) : insights.data.items === 0 ? (
        <EmptyState
          icon={<ChartColumn />}
          title="Nothing to show yet"
          action={
            <Button asChild>
              <Link href="/wardrobe/new">Add an item</Link>
            </Button>
          }
        >
          Add what you own and log what you wear; this page fills in from there.
        </EmptyState>
      ) : (
        <WardrobeData>
          {({ reference }) => (
            <Sections data={insights.data} reference={reference} />
          )}
        </WardrobeData>
      )}
    </div>
  );
}

function Sections({
  data,
  reference,
}: {
  data: Insights;
  reference: Reference;
}) {
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const occasions = new Map(reference.occasions.map((o) => [o.id, o.name]));
  const seasons = new Map(reference.seasons.map((s) => [s.id, s.name]));
  const toGo = data.needed_logs - data.logs;

  return (
    <div className="flex flex-col gap-8">
      <p className="text-ink-soft">
        {data.items} {data.items === 1 ? "item" : "items"} · {data.logs}{" "}
        {data.logs === 1 ? "day" : "days"} of wear logged ·{" "}
        {data.days_logged_30} in the last 30 days
      </p>
      {!data.enough && (
        <Alert>
          Log what you wear on {toGo} more {toGo === 1 ? "day" : "days"} to see
          your most and least worn pieces and the style you actually wear.
        </Alert>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {data.enough && (
          <>
            <Card>
              <CardTitle>Most worn</CardTitle>
              <ItemList rows={data.most_worn} familyHex={familyHex} />
            </Card>
            <Card>
              <CardTitle>Least worn</CardTitle>
              <CardDescription className="mt-1">
                Among things you&apos;ve had for a month or more.
              </CardDescription>
              <ItemList rows={data.least_worn} familyHex={familyHex} />
            </Card>
          </>
        )}
        <MonthBars months={data.by_month} />
        <Card>
          <CardTitle>What you wear</CardTitle>
          <CardDescription className="mt-1">
            Pieces worn, by kind and by colour.
          </CardDescription>
          {data.by_group.length === 0 ? (
            <p className="mt-3 text-sm text-ink-soft">Nothing logged yet.</p>
          ) : (
            <div className="mt-4 flex flex-col gap-5">
              <Bars
                label="By kind"
                rows={data.by_group.map((row) => ({
                  key: row.id,
                  name: row.name,
                  value: row.wears,
                }))}
              />
              <Bars
                label="By colour"
                rows={data.by_color.map((row) => ({
                  key: row.id,
                  name: row.name,
                  value: row.wears,
                  swatch: row.hex,
                }))}
              />
            </div>
          )}
        </Card>
      </div>

      <section aria-labelledby="value-heading" className="flex flex-col gap-4">
        <h2 id="value-heading" className="text-lg font-medium">
          Cost per wear
        </h2>
        <p className="max-w-prose text-sm text-ink-soft">
          The price you paid divided by the times you&apos;ve worn it, for
          pieces with a price.
        </p>
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardTitle>Best value</CardTitle>
            {data.cheapest.length === 0 ? (
              <p className="mt-3 text-sm text-ink-soft">
                Nothing with a price has been worn yet.
              </p>
            ) : (
              <CostList rows={data.cheapest} familyHex={familyHex} />
            )}
          </Card>
          {data.dearest.length > 0 && (
            <Card>
              <CardTitle>Most per wear</CardTitle>
              <CostList rows={data.dearest} familyHex={familyHex} />
            </Card>
          )}
          {data.needs_price.length > 0 && (
            <Card>
              <CardTitle>Add a price</CardTitle>
              <CardDescription className="mt-1">
                Worn, but without a price, so there&apos;s no cost per wear.
              </CardDescription>
              <ul className="mt-3 flex flex-col gap-2">
                {data.needs_price.map((item) => (
                  <li key={item.id}>
                    <ItemRow item={item} familyHex={familyHex}>
                      <Link
                        href={`/wardrobe/${item.id}/edit`}
                        className={cn(
                          "rounded text-sm font-medium text-indigo underline underline-offset-4",
                          focusRing,
                        )}
                      >
                        Add a price{" "}
                        <span className="sr-only">for {item.display_name}</span>
                      </Link>
                    </ItemRow>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </section>

      <section aria-labelledby="graph-heading" className="flex flex-col gap-4">
        <h2 id="graph-heading" className="text-lg font-medium">
          What your wardrobe can do
        </h2>
        {data.coverage === null ? (
          <Alert>
            Choose the occasions you dress for (in Settings, or your usual week
            in My Week) to see how many good outfits each piece makes and where
            your wardrobe is thin.
          </Alert>
        ) : (
          <>
            <p className="max-w-prose text-sm text-ink-soft">
              Counted over everything you own except retired pieces, as if all
              of it were clean, for the occasions you dress for.
            </p>
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardTitle>Most versatile</CardTitle>
                <CardDescription className="mt-1">
                  Good outfits each piece is part of.
                </CardDescription>
                <ul className="mt-3 flex flex-col gap-2">
                  {(data.versatile ?? []).map((row) => (
                    <li key={row.item.id}>
                      <ItemRow item={row.item} familyHex={familyHex}>
                        <span className="text-sm text-ink-soft tabular-nums">
                          {row.outfits} outfits
                        </span>
                      </ItemRow>
                    </li>
                  ))}
                </ul>
              </Card>
              <Card>
                <CardTitle>Go with little</CardTitle>
                <CardDescription className="mt-1">
                  In fewer than two good outfits, and what would help.
                </CardDescription>
                {(data.orphans ?? []).length === 0 ? (
                  <p className="mt-3 text-sm text-ink-soft">
                    Every piece is part of at least two good outfits.
                  </p>
                ) : (
                  <ul className="mt-3 flex flex-col gap-3">
                    {(data.orphans ?? []).map((row) => (
                      <li key={row.item.id} className="flex flex-col gap-1">
                        <ItemRow item={row.item} familyHex={familyHex}>
                          <span className="text-sm text-ink-soft tabular-nums">
                            {row.outfits === 1
                              ? "1 outfit"
                              : `${row.outfits} outfits`}
                          </span>
                        </ItemRow>
                        <p className="pl-16 text-sm">{row.rescue}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>
            <Coverage
              coverage={data.coverage}
              occasions={occasions}
              seasons={seasons}
            />
          </>
        )}
      </section>

      {data.style && <StyleSection style={data.style} familyHex={familyHex} />}

      <section
        aria-labelledby="declutter-heading"
        className="flex flex-col gap-4"
      >
        <h2 id="declutter-heading" className="text-lg font-medium">
          Worth a second look
        </h2>
        {data.declutter.length === 0 ? (
          <p className="text-sm text-ink-soft">
            Nothing to suggest: everything has been worn in the last six months
            or goes into a couple of good outfits.
          </p>
        ) : (
          <>
            <p className="max-w-prose text-sm text-ink-soft">
              Not worn in six months and part of almost no good outfits. Keep
              what you love; these are only suggestions.
            </p>
            <ul className="flex flex-col gap-2">
              {data.declutter.map((row) => (
                <li key={row.item.id}>
                  <ItemRow item={row.item} familyHex={familyHex}>
                    <span className="text-right text-sm text-ink-soft">
                      {row.last_worn_on
                        ? `Last worn ${dayPhrase(row.last_worn_on)}`
                        : `Not worn since you added it ${dayPhrase(row.added_on)}`}
                      {" · "}
                      {row.outfits === 1
                        ? "in 1 good outfit"
                        : `in ${row.outfits} good outfits`}
                    </span>
                  </ItemRow>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}

function ItemRow({
  item,
  familyHex,
  children,
}: {
  item: Brief;
  familyHex: Map<string, string | null>;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full">
        <ItemPhoto
          photo={item.photo}
          alt=""
          hex={item.color_hex ?? familyHex.get(item.color_primary)}
        />
      </span>
      <Link
        href={`/wardrobe/${item.id}`}
        className={cn(
          "min-w-0 flex-1 truncate rounded hover:underline",
          focusRing,
        )}
      >
        {item.display_name}
      </Link>
      {children}
    </div>
  );
}

function ItemList({
  rows,
  familyHex,
}: {
  rows: WornRow[];
  familyHex: Map<string, string | null>;
}) {
  if (rows.length === 0) {
    return <p className="mt-3 text-sm text-ink-soft">Nothing yet.</p>;
  }
  return (
    <ul className="mt-3 flex flex-col gap-2">
      {rows.map((row) => (
        <li key={row.item.id}>
          <ItemRow item={row.item} familyHex={familyHex}>
            <span className="text-right text-sm text-ink-soft">
              <span className="tabular-nums">
                {row.wears === 1 ? "1 wear" : `${row.wears} wears`}
              </span>
              {row.last_worn_on && (
                <span className="block">
                  last {dayPhrase(row.last_worn_on)}
                </span>
              )}
            </span>
          </ItemRow>
        </li>
      ))}
    </ul>
  );
}

function CostList({
  rows,
  familyHex,
}: {
  rows: CostRow[];
  familyHex: Map<string, string | null>;
}) {
  return (
    <ul className="mt-3 flex flex-col gap-2">
      {rows.map((row) => (
        <li key={row.item.id}>
          <ItemRow item={row.item} familyHex={familyHex}>
            <span className="text-right text-sm">
              <span className="font-medium tabular-nums">
                {formatRupees(row.per_wear)}
              </span>
              <span className="block text-ink-soft">
                {formatRupees(row.price)} ÷ {row.wears}
              </span>
            </span>
          </ItemRow>
        </li>
      ))}
    </ul>
  );
}

type BarRow = {
  key: string;
  name: string;
  value: number;
  /** The number as shown, when it isn't the plain value ("57%"). */
  text?: string;
  swatch?: string | null;
};

/** Horizontal bars, one neutral colour; each row says its name and number in text. */
function Bars({ label, rows }: { label: string; rows: BarRow[] }) {
  const max = Math.max(1, ...rows.map((row) => row.value));
  const id = useId();
  return (
    <div>
      <h3 id={id} className="mb-2 text-sm font-medium">
        {label}
      </h3>
      <ul aria-labelledby={id} className="flex flex-col gap-1.5">
        {rows.map((row) => (
          <li
            key={row.key}
            className="grid grid-cols-[minmax(0,9rem)_1fr_2.5rem] items-center gap-3 text-sm"
          >
            <span className="flex min-w-0 items-center gap-2">
              {row.swatch !== undefined && (
                <span
                  aria-hidden
                  className="size-3 shrink-0 rounded-sm border border-line-strong/40"
                  style={{ background: row.swatch ?? undefined }}
                />
              )}
              <span className="truncate">{row.name}</span>
            </span>
            <span className="h-2.5 rounded-r bg-tile">
              <span
                className="block h-full rounded-r bg-ink-soft"
                style={{ width: `${(row.value / max) * 100}%` }}
              />
            </span>
            <span className="text-right text-ink-soft tabular-nums">
              {row.text ?? row.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MonthBars({ months }: { months: Insights["by_month"] }) {
  const max = Math.max(1, ...months.map((row) => row.days));
  const titleId = useId();
  return (
    <Card>
      <CardTitle id={titleId}>Days logged</CardTitle>
      <CardDescription className="mt-1">The last six months.</CardDescription>
      <div aria-hidden className="mt-4 flex h-40 items-end gap-3">
        {months.map((row) => (
          <div
            key={row.month}
            className="flex h-full flex-1 flex-col items-center justify-end gap-1"
            title={`${monthLabel(row.month)}: ${row.days} days`}
          >
            <span className="text-xs text-ink-soft tabular-nums">
              {row.days > 0 ? row.days : ""}
            </span>
            <span
              className="w-full max-w-10 rounded-t bg-ink-soft"
              style={{
                height: `${(row.days / max) * 75}%`,
                minHeight: row.days ? 4 : 0,
              }}
            />
            <span className="h-px w-full bg-line" />
            <span className="text-xs text-ink-soft">
              {monthLabel(row.month).split(" ")[0]}
            </span>
          </div>
        ))}
      </div>
      <table className="sr-only" aria-labelledby={titleId}>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">Days logged</th>
          </tr>
        </thead>
        <tbody>
          {months.map((row) => (
            <tr key={row.month}>
              <td>{monthLabel(row.month)}</td>
              <td>{row.days}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Coverage({
  coverage,
  occasions,
  seasons,
}: {
  coverage: NonNullable<Insights["coverage"]>;
  occasions: Map<string, string>;
  seasons: Map<string, string>;
}) {
  const cell = new Map(
    coverage.cells.map((entry) => [
      `${entry.occasion_id}:${entry.season}`,
      entry,
    ]),
  );
  return (
    <Card>
      <CardTitle>Good outfits by occasion and season</CardTitle>
      <CardDescription className="mt-1">
        Different outfits that score well. &ldquo;None&rdquo; is a gap.
      </CardDescription>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[28rem] border-separate border-spacing-1 text-sm">
          <thead>
            <tr>
              <th scope="col" className="text-left font-medium text-ink-soft">
                <span className="sr-only">Occasion</span>
              </th>
              {coverage.seasons.map((season) => (
                <th
                  key={season}
                  scope="col"
                  className="font-medium text-ink-soft"
                >
                  {seasons.get(season) ?? season}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {coverage.occasion_ids.map((occasion) => (
              <tr key={occasion}>
                <th scope="row" className="pr-2 text-left font-normal">
                  {occasions.get(occasion) ?? occasion}
                </th>
                {coverage.seasons.map((season) => {
                  const entry = cell.get(`${occasion}:${season}`);
                  const count = entry?.outfits ?? 0;
                  return (
                    <td
                      key={season}
                      className={cn(
                        "rounded-md px-2 py-2 text-center tabular-nums",
                        count === 0 ? "bg-paper font-medium" : "bg-tile",
                      )}
                    >
                      {count === 0 ? "None" : entry?.capped ? "10+" : count}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function StyleSection({
  style,
  familyHex,
}: {
  style: NonNullable<Insights["style"]>;
  familyHex: Map<string, string | null>;
}) {
  return (
    <section aria-labelledby="style-heading" className="flex flex-col gap-4">
      <h2 id="style-heading" className="text-lg font-medium">
        The style you actually wear
      </h2>
      <p className="max-w-prose text-sm text-ink-soft">
        From {style.wears} wears of clothes and shoes.
      </p>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardTitle>Your colours</CardTitle>
          <div className="mt-4">
            <Bars
              label="Share of wears"
              rows={style.palette.slice(0, 6).map((row) => ({
                key: row.id,
                name: row.name,
                value: row.share,
                text: percent(row.share),
                swatch: row.hex ?? familyHex.get(row.id) ?? null,
              }))}
            />
          </div>
        </Card>
        <Card>
          <CardTitle>How dressed up</CardTitle>
          <div className="mt-4">
            <Bars
              label="Share of wears, casual to formal"
              rows={style.formality.map((row) => ({
                key: row.id,
                name: row.name,
                value: row.share,
                text: percent(row.share),
              }))}
            />
          </div>
        </Card>
        {style.styles.length > 0 && (
          <Card className="md:col-span-2">
            <CardTitle>Styles your wears match</CardTitle>
            <ul className="mt-3 flex flex-wrap gap-2">
              {style.styles.slice(0, 6).map((row) => (
                <li
                  key={row.id}
                  className="rounded-full bg-tile px-3 py-1 text-sm"
                >
                  {row.name} · {percent(row.share)}
                  {row.chosen && (
                    <span className="text-ink-soft"> · you chose it</span>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </section>
  );
}
