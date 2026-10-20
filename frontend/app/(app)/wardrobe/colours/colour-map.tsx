"use client";

import { useQuery } from "@tanstack/react-query";
import { Palette } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import type { Reference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";

type Point = components["schemas"]["ColourPoint"];

// The plot: hue across (0 to 360 degrees), lightness up; neutrals on their own strip below,
// by lightness, since they have no hue to speak of.
const WIDTH = 360;
const TOP = 12;
const CHROMATIC = 170;
const STRIP = 200;
const HEIGHT = 228;
const HUES = [
  [0, "Red"],
  [70, "Yellow"],
  [140, "Green"],
  [230, "Blue"],
  [310, "Purple"],
] as const;

function place(point: Point): [number, number] {
  if (point.neutral) return [8 + point.lightness * (WIDTH - 16), STRIP];
  return [point.hue, TOP + (1 - point.lightness) * (CHROMATIC - TOP)];
}

export function ColourMap() {
  const points = useQuery({
    queryKey: ["items", "colours"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/items/colours");
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
  });

  return (
    <div className="flex max-w-5xl flex-col gap-6">
      <BackLink href="/wardrobe">Wardrobe</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Colour map
        </h1>
        <p className="mt-1 max-w-prose text-ink-soft">
          Your wardrobe by colour, as WearWise sees it: hue across, light at the
          top and dark at the bottom, and neutrals on their own line. Press a
          colour to see those pieces.
        </p>
      </div>
      {points.isError ? (
        <ErrorState
          title="Couldn't load your colours"
          action={
            <Button variant="secondary" onClick={() => void points.refetch()}>
              Try again
            </Button>
          }
        >
          Check your connection and try again.
        </ErrorState>
      ) : !points.data ? (
        <Skeleton className="h-72" />
      ) : points.data.length === 0 ? (
        <EmptyState
          icon={<Palette />}
          title="Nothing to map yet"
          action={
            <Button asChild>
              <Link href="/wardrobe/new">Add an item</Link>
            </Button>
          }
        >
          Add what you own and it appears here by colour.
        </EmptyState>
      ) : (
        <WardrobeData>
          {({ reference }) => (
            <ColourPlot points={points.data} reference={reference} />
          )}
        </WardrobeData>
      )}
    </div>
  );
}

function ColourPlot({
  points,
  reference,
}: {
  points: Point[];
  reference: Reference;
}) {
  const router = useRouter();
  const families = reference.color_families;
  const shown = points.filter((point) => point.known);
  const groups = families
    .map((family) => ({
      family,
      items: shown.filter((point) => point.color_primary === family.id),
    }))
    .filter((group) => group.items.length > 0);
  const multi = points.filter((point) => !point.known).length;
  const filter = (family: string) => router.push(`/wardrobe?color=${family}`);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
      <Card>
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="w-full"
          role="group"
          aria-label={`${shown.length} pieces plotted by colour`}
        >
          <rect
            x="0"
            y="0"
            width={WIDTH}
            height={CHROMATIC + 4}
            rx="8"
            className="fill-tile"
          />
          <rect
            x="0"
            y={STRIP - 14}
            width={WIDTH}
            height="28"
            rx="8"
            className="fill-tile"
          />
          {HUES.map(([hue, name]) => (
            <text
              key={name}
              x={hue + 4}
              y={CHROMATIC + 16}
              className="fill-ink-soft text-[9px]"
              aria-hidden
            >
              {name}
            </text>
          ))}
          <text
            x="4"
            y={HEIGHT - 2}
            className="fill-ink-soft text-[9px]"
            aria-hidden
          >
            Neutrals, dark to light
          </text>
          {shown.map((point) => {
            const [x, y] = place(point);
            return (
              <circle
                key={point.id}
                cx={x}
                cy={y}
                r="6"
                fill={point.hex ?? undefined}
                className="stroke-line-strong"
                strokeWidth="1"
                aria-hidden
              />
            );
          })}
          {groups.map(({ family, items }) => {
            const spots = items.map(place);
            const cx = spots.reduce((sum, [x]) => sum + x, 0) / spots.length;
            const cy = spots.reduce((sum, [, y]) => sum + y, 0) / spots.length;
            const r =
              Math.max(
                ...spots.map(([x, y]) => Math.hypot(x - cx, y - cy)),
                0,
              ) + 10;
            return (
              <circle
                key={family.id}
                cx={cx}
                cy={cy}
                r={r}
                role="button"
                tabIndex={0}
                aria-label={`${family.name}: ${items.length} ${items.length === 1 ? "piece" : "pieces"}`}
                className={cn(
                  "cursor-pointer fill-transparent stroke-transparent hover:stroke-ink-soft focus-visible:stroke-indigo",
                  "outline-none",
                )}
                strokeWidth="1.5"
                strokeDasharray="3 3"
                onClick={() => filter(family.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    filter(family.id);
                  }
                }}
              />
            );
          })}
        </svg>
        {multi > 0 && (
          <p className="mt-2 text-sm text-ink-soft">
            {multi} multicolour {multi === 1 ? "piece isn't" : "pieces aren't"}{" "}
            plotted: they have no single colour.
          </p>
        )}
      </Card>
      <Card>
        <CardTitle>By colour</CardTitle>
        <CardDescription className="mt-1">
          Press one to see those pieces.
        </CardDescription>
        <ul className="mt-3 flex flex-col gap-1">
          {groups
            .sort((a, b) => b.items.length - a.items.length)
            .map(({ family, items }) => (
              <li key={family.id}>
                <Link
                  href={`/wardrobe?color=${family.id}`}
                  className={cn(
                    "flex min-h-11 items-center gap-3 rounded-lg px-2 hover:bg-tile",
                    focusRing,
                  )}
                >
                  <span
                    aria-hidden
                    className="size-4 shrink-0 rounded-sm border border-line-strong/40"
                    style={{ background: family.hex ?? undefined }}
                  />
                  <span className="flex-1">{family.name}</span>
                  <span className="text-sm text-ink-soft tabular-nums">
                    {items.length}
                  </span>
                </Link>
              </li>
            ))}
        </ul>
      </Card>
    </div>
  );
}
