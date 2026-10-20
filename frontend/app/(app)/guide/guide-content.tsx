"use client";

import { Check } from "lucide-react";

import { BrandNotes } from "@/components/profile/brand-notes";
import { PieceRow } from "@/components/shopping/piece-row";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";
import { WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import type { Reference } from "@/lib/profile";
import {
  type Guide,
  type Staple,
  useAddStaple,
  useGuide,
} from "@/lib/shopping";
import { cn, focusRing } from "@/lib/utils";

export function GuideContent() {
  const guide = useGuide();
  return (
    <div className="flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Style Guide
        </h1>
        <p className="mt-1 max-w-prose text-ink-soft">
          Fabrics, styles, and colour basics, and your own notes on brands.
        </p>
      </div>
      {guide.isError ? (
        <ErrorState
          title="Couldn't load the guide"
          action={
            <Button variant="secondary" onClick={() => void guide.refetch()}>
              Try again
            </Button>
          }
        >
          Check your connection and try again.
        </ErrorState>
      ) : !guide.data ? (
        <div aria-busy="true" className="flex flex-col gap-3">
          <Skeleton className="h-10 w-80" />
          <Skeleton className="h-64" />
        </div>
      ) : (
        <WardrobeData>
          {({ reference }) => (
            <Sections guide={guide.data} reference={reference} />
          )}
        </WardrobeData>
      )}
    </div>
  );
}

function Sections({
  guide,
  reference,
}: {
  guide: Guide;
  reference: Reference;
}) {
  const seasons = new Map(reference.seasons.map((s) => [s.id, s.name]));
  return (
    <Tabs defaultValue="fabrics">
      <TabsList
        aria-label="Style Guide sections"
        className="gap-x-2 sm:gap-x-4"
      >
        <TabsTrigger value="fabrics">Fabrics</TabsTrigger>
        <TabsTrigger value="styles">Styles</TabsTrigger>
        <TabsTrigger value="colours">Colours</TabsTrigger>
        <TabsTrigger value="brands">Brands</TabsTrigger>
      </TabsList>

      <TabsContent value="fabrics">
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {guide.fabrics.map((fabric) => (
            <li key={fabric.id}>
              <Card className="h-full">
                <CardTitle>{fabric.name}</CardTitle>
                <CardDescription className="mt-1">
                  {fabric.feel}
                </CardDescription>
                <dl className="mt-3 flex flex-col gap-2 text-sm">
                  <Row term="Best in">
                    {fabric.seasons.length === 4
                      ? "Any season"
                      : fabric.seasons
                          .map((s) => seasons.get(s) ?? s)
                          .join(", ")}
                  </Row>
                  <Row term="Care">{fabric.care}</Row>
                  <Row term="On the label">{fabric.label}</Row>
                  <Row term="Watch out">{fabric.watch}</Row>
                </dl>
              </Card>
            </li>
          ))}
        </ul>
      </TabsContent>

      <TabsContent value="styles">
        <p className="mb-4 max-w-prose text-sm text-ink-soft">
          What each style is built on, and which of those staples you already
          have: something you own that&apos;s close enough to count.
        </p>
        <ul className="flex flex-col gap-4">
          {[
            ...guide.styles.filter((style) => style.chosen),
            ...guide.styles.filter((style) => !style.chosen),
          ].map((style) => (
            <li key={style.id}>
              <Card>
                <CardTitle>
                  {style.name}
                  {style.chosen && (
                    <span className="ml-2 text-sm font-normal text-ink-soft">
                      Your style
                    </span>
                  )}
                </CardTitle>
                <CardDescription className="mt-1">
                  {style.description}
                </CardDescription>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-ink-soft">Colours:</span>
                  {style.colors.map((colour) => (
                    <span
                      key={colour.id}
                      className="inline-flex items-center gap-1.5"
                    >
                      <span
                        aria-hidden
                        className="size-3 rounded-sm border border-line-strong/40"
                        style={{ background: colour.hex ?? undefined }}
                      />
                      {colour.name}
                    </span>
                  ))}
                </div>
                {style.fabrics.length > 0 && (
                  <p className="mt-1 text-sm">
                    <span className="text-ink-soft">Fabrics:</span>{" "}
                    {style.fabrics.join(", ")}
                  </p>
                )}
                {style.pieces.length > 0 && (
                  <details open={style.chosen} className="mt-4">
                    <summary
                      className={cn(
                        "min-h-11 cursor-pointer rounded-lg py-2 text-sm font-medium",
                        focusRing,
                      )}
                    >
                      You have {style.pieces.filter((p) => p.owned).length} of
                      its {style.pieces.length} staples
                    </summary>
                    <ul className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
                      {style.pieces.map((piece) => (
                        <li key={piece.staple.id}>
                          <StyleStaple
                            staple={piece.staple}
                            owned={piece.owned}
                          />
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </Card>
            </li>
          ))}
        </ul>
      </TabsContent>

      <TabsContent value="colours">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {guide.colour.map((entry) => (
            <Card
              key={entry.id}
              className={entry.id === "neutrals" ? "md:col-span-2" : undefined}
            >
              <CardTitle>{entry.title}</CardTitle>
              <p className="mt-2 max-w-prose text-sm">{entry.text}</p>
              {entry.id === "neutrals" && (
                <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm">
                  {guide.neutrals.map((family) => (
                    <li
                      key={family.id}
                      className="inline-flex items-center gap-1.5"
                    >
                      <span
                        aria-hidden
                        className="size-4 rounded-sm border border-line-strong/40"
                        style={{ background: family.hex ?? undefined }}
                      />
                      {family.name}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
        </div>
      </TabsContent>

      <TabsContent value="brands">
        <p className="mb-4 max-w-prose text-sm text-ink-soft">
          Your own notes on how each brand fits, wears, and prices. The same
          notes are in Settings.
        </p>
        <BrandNotes />
      </TabsContent>
    </Tabs>
  );
}

function Row({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="font-medium">{term}</dt>
      <dd className="text-ink-soft">{children}</dd>
    </div>
  );
}

function StyleStaple({
  staple,
  owned,
}: {
  staple: Staple;
  owned: Guide["styles"][number]["pieces"][number]["owned"];
}) {
  const add = useAddStaple();
  async function addStaple() {
    try {
      await add.mutateAsync(staple.id);
      toast.success(`${staple.name} added to your list`);
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }
  return (
    <PieceRow name={staple.name} hex={staple.hex}>
      {owned ? (
        <span className="inline-flex shrink-0 items-center gap-1 text-right text-sm text-ink-soft">
          <Check aria-hidden className="size-4" />
          <span className="sr-only">You have it: </span>
          {owned.display_name}
        </span>
      ) : staple.on_list ? (
        <span className="shrink-0 text-sm text-ink-soft">On your list</span>
      ) : (
        <Button
          variant="quiet"
          className="shrink-0"
          disabled={add.isPending}
          onClick={() => void addStaple()}
        >
          Add to list<span className="sr-only">: {staple.name}</span>
        </Button>
      )}
    </PieceRow>
  );
}
