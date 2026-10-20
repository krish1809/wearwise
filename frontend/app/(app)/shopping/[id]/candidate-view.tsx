"use client";

import { Clock, ExternalLink, Pencil, ShoppingBag } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { PageLoading } from "@/components/app-shell";
import { OutfitBoard } from "@/components/outfits/outfit-board";
import { ReasonList } from "@/components/outfits/reason-list";
import { OwnedRow } from "@/components/shopping/piece-row";
import { ShopPanel } from "@/components/shopping/shop-panel";
import { TryOn } from "@/components/shopping/try-on";
import { VerdictBadge } from "@/components/shopping/verdict-badge";
import { WAITING, WaitPicker } from "@/components/shopping/wait-picker";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { FilterChip } from "@/components/ui/chip";
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
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { ApiRequestError, problemFrom } from "@/lib/api/errors";
import { dayPhrase, todayIso } from "@/lib/dates";
import {
  AMOUNT_ERROR,
  MAX_RUPEES,
  formatRupees,
  paiseToRupeesText,
  rupeesToPaise,
} from "@/lib/money";
import type { Reference } from "@/lib/profile";
import {
  type Analysis,
  type Candidate,
  needsOccasions,
  priceMayHaveChanged,
  siteOf,
  STATUSES,
  useAnalysis,
  useCandidate,
  useDeleteCandidate,
  usePurchase,
  useUpdateCandidate,
} from "@/lib/shopping";
import { cn, focusRing } from "@/lib/utils";

import { NeedsOccasions } from "../shopping-content";

export function CandidateView() {
  const { id } = useParams<{ id: string }>();
  const candidate = useCandidate(id);

  if (
    candidate.error instanceof ApiRequestError &&
    candidate.error.problem.code === "candidate_not_found"
  ) {
    return (
      <EmptyState
        title="That isn't on your shopping list"
        action={
          <Button asChild variant="secondary">
            <Link href="/shopping">Go to Shopping</Link>
          </Button>
        }
      >
        It may have been deleted.
      </EmptyState>
    );
  }
  if (candidate.isError) {
    return (
      <ErrorState
        title="Couldn't load this"
        action={
          <Button variant="secondary" onClick={() => void candidate.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!candidate.data) return <PageLoading />;
  return (
    <WardrobeData>
      {({ reference }) => (
        <Details candidate={candidate.data} reference={reference} />
      )}
    </WardrobeData>
  );
}

function Details({
  candidate,
  reference,
}: {
  candidate: Candidate;
  reference: Reference;
}) {
  const bought = candidate.status === "purchased";
  const analysis = useAnalysis(candidate.id, !bought);
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));

  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/shopping">Shopping</BackLink>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <div className="flex aspect-square items-center justify-center rounded-xl bg-tile p-6 *:max-h-full *:max-w-full">
            <ItemPhoto
              photo={candidate.photo}
              imageUrl={candidate.image_url}
              alt={candidate.display_name}
              hex={
                candidate.color_hex ?? familyHex.get(candidate.color_primary)
              }
              size="full"
              className="rounded-lg"
            />
          </div>
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight">
              {candidate.display_name}
            </h1>
            {candidate.brand && (
              <p className="text-ink-soft">{candidate.brand}</p>
            )}
          </div>
          <Facts candidate={candidate} />
          {bought ? (
            <Alert>
              You bought this.{" "}
              {candidate.item_id && (
                <Link
                  href={`/wardrobe/${candidate.item_id}`}
                  className={cn("underline underline-offset-4", focusRing)}
                >
                  See it in your wardrobe
                </Link>
              )}
            </Alert>
          ) : (
            <>
              <StatusPicker candidate={candidate} />
              {WAITING.includes(candidate.status) && (
                <WaitPicker candidate={candidate} />
              )}
              <div className="flex flex-wrap gap-3">
                <PurchaseDialog candidate={candidate} />
                <Button asChild variant="secondary">
                  <Link href={`/shopping/${candidate.id}/edit`}>
                    <Pencil aria-hidden />
                    Edit
                  </Link>
                </Button>
                <DeleteDialog candidate={candidate} />
              </div>
            </>
          )}
        </div>

        {!bought && (
          <section
            aria-labelledby="adds-heading"
            className="flex flex-col gap-6"
          >
            <h2 id="adds-heading" className="sr-only">
              What it would add
            </h2>
            {needsOccasions(analysis.error) ? (
              <NeedsOccasions />
            ) : analysis.isError ? (
              <ErrorState
                title="Couldn't work out what it would add"
                action={
                  <Button
                    variant="secondary"
                    onClick={() => void analysis.refetch()}
                  >
                    Try again
                  </Button>
                }
              >
                {problemFrom(analysis.error).message}
              </ErrorState>
            ) : !analysis.data ? (
              <div aria-busy="true" className="flex flex-col gap-4">
                <Skeleton className="h-36" />
                <Skeleton className="h-48" />
                <span role="status" className="sr-only">
                  Working out what it would add
                </span>
              </div>
            ) : (
              <AnalysisPanel
                analysis={analysis.data}
                candidate={candidate}
                reference={reference}
              />
            )}
          </section>
        )}
      </div>
    </div>
  );
}

const SOURCES: Record<string, string> = {
  manual: "Added by you",
  archetype: "A wardrobe staple, not a product",
  catalog: "From the demo catalogue: an example, not for sale",
};

function Facts({ candidate }: { candidate: Candidate }) {
  const site = siteOf(candidate.url);
  const read = candidate.source === "link";
  const stale = priceMayHaveChanged(candidate.price_checked_at);
  const rows: [string, React.ReactNode][] = [
    [
      "From",
      read && site
        ? `${site}, read from the page you pasted`
        : (site ?? SOURCES[candidate.source] ?? "Added by you"),
    ],
  ];
  if (candidate.price !== null) {
    rows.push([
      "Price",
      <>
        <span className="tabular-nums">{formatRupees(candidate.price)}</span>
        {candidate.price_checked_at && (
          <span className="text-ink-soft">
            {" "}
            · {read ? "checked" : "noted"}{" "}
            {dayPhrase(candidate.price_checked_at.slice(0, 10))}
          </span>
        )}
        {stale && (
          <span className="mt-0.5 flex items-center gap-1 text-consider">
            <Clock aria-hidden className="size-4" />
            May have changed since
          </span>
        )}
      </>,
    ]);
  }
  if (candidate.target_price !== null) {
    rows.push(["You'd pay", formatRupees(candidate.target_price)]);
  }
  if (candidate.size_label) rows.push(["Size", candidate.size_label]);
  return (
    <div className="flex flex-col gap-3">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {rows.map(([term, value]) => (
          <div key={term} className="contents">
            <dt className="text-ink-soft">{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {candidate.url ? (
        <a
          href={candidate.url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className={cn(
            "inline-flex items-center gap-1.5 self-start rounded text-sm font-medium text-indigo underline underline-offset-4",
            focusRing,
          )}
        >
          See it in the shop
          <ExternalLink aria-hidden className="size-4" />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      ) : (
        candidate.status !== "purchased" && (
          <ShopPanel
            target={{ candidateId: candidate.id }}
            name={candidate.display_name}
            trigger={
              <Button variant="secondary" className="self-start">
                <ShoppingBag aria-hidden />
                Find it in shops
              </Button>
            }
          />
        )
      )}
      {candidate.notes && <p className="text-sm">{candidate.notes}</p>}
    </div>
  );
}

function StatusPicker({ candidate }: { candidate: Candidate }) {
  const update = useUpdateCandidate(candidate.id);
  const open = STATUSES.filter((status) => status.id !== "purchased");

  async function choose(status: string, undoable = true) {
    const before = candidate.status;
    try {
      await update.mutateAsync({ status });
      if (status === "skipped" && undoable) {
        toast.success("Skipped", {
          action: { label: "Undo", onClick: () => void choose(before, false) },
        });
      }
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <div
      role="radiogroup"
      aria-label="Where it stands"
      className="flex flex-wrap gap-2"
    >
      {open.map((status) => (
        <FilterChip
          key={status.id}
          role="radio"
          aria-checked={candidate.status === status.id}
          selected={candidate.status === status.id}
          disabled={update.isPending}
          onClick={() => void choose(status.id)}
        >
          {status.name}
        </FilterChip>
      ))}
    </div>
  );
}

function AnalysisPanel({
  analysis,
  candidate,
  reference,
}: {
  analysis: Analysis;
  candidate: Candidate;
  reference: Reference;
}) {
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));
  const core = analysis.kind === "core";
  const alike = Math.round(analysis.redundancy * 100);

  return (
    <>
      <Card>
        <p className="text-sm text-ink-soft">Verdict</p>
        <VerdictBadge
          verdict={analysis.verdict}
          size="large"
          className="mt-1"
        />
        <ReasonList reasons={analysis.reasons} className="mt-4" />
      </Card>

      <Card>
        <CardTitle>The numbers</CardTitle>
        <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          <Fact
            term={core ? "New good outfits" : "Good outfits it finishes"}
            value={String(analysis.new_outfits)}
          />
          {analysis.cost_per_new_outfit !== null && (
            <Fact
              term="Cost per new outfit"
              value={formatRupees(analysis.cost_per_new_outfit)}
            />
          )}
          {analysis.closest && (
            <Fact
              term="Closest you own"
              value={`${analysis.closest.display_name}, ${alike}% alike`}
            />
          )}
          {analysis.usual_spend !== null && candidate.price !== null && (
            <Fact
              term="Your usual spend"
              value={`${formatRupees(analysis.usual_spend)}: ${
                analysis.within_budget ? "within it" : "this costs more"
              }`}
            />
          )}
          {analysis.projected && (
            <Fact
              term="Cost per wear (estimate)"
              value={`About ${formatRupees(analysis.projected.per_wear)}, if you wear it as often as your other ${analysis.projected.similar === 1 ? "one" : `${analysis.projected.similar}`} like it (about ${analysis.projected.wears_a_year} times a year)`}
            />
          )}
        </dl>
      </Card>

      {core && <Coverage analysis={analysis} reference={reference} />}

      {core && (
        <TryOn
          candidate={candidate}
          reference={reference}
          occasionIds={[
            ...new Set(analysis.cells.map((cell) => cell.occasion_id)),
          ]}
        />
      )}

      {analysis.examples.length > 0 && (
        <section
          aria-labelledby="examples-heading"
          className="flex flex-col gap-3"
        >
          <h3 id="examples-heading" className="font-medium">
            {core ? "Outfits it would make" : "Outfits it would finish"}
          </h3>
          <ul className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-3">
            {analysis.examples.map((example, index) => (
              <li key={index}>
                <OutfitBoard
                  size="small"
                  slots={slots}
                  familyHex={familyHex}
                  pieces={example.pieces.map((piece) =>
                    piece.item
                      ? {
                          slot: piece.item.slot,
                          name: piece.item.display_name,
                          removed: false,
                          item: piece.item,
                        }
                      : {
                          slot: candidate.slot,
                          name: candidate.display_name,
                          removed: false,
                          item: {
                            color_primary: candidate.color_primary,
                            color_hex: candidate.color_hex,
                            photo: candidate.photo,
                          },
                        },
                  )}
                />
                <p className="mt-1 text-sm text-ink-soft">
                  {example.pieces
                    .map((piece) =>
                      piece.item
                        ? piece.item.display_name
                        : `this ${candidate.display_name.toLowerCase()}`,
                    )
                    .join(", ")}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {analysis.matches.length > 0 && (
        <Card>
          <CardTitle>
            Goes with {analysis.matches.length}{" "}
            {analysis.matches.length === 1 ? "thing" : "things"} you own
          </CardTitle>
          <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {analysis.matches.slice(0, 8).map((match) => (
              <li key={match.item.id}>
                <OwnedRow item={match.item} familyHex={familyHex} />
              </li>
            ))}
          </ul>
          {analysis.matches.length > 8 && (
            <p className="mt-2 text-sm text-ink-soft">
              And {analysis.matches.length - 8} more.
            </p>
          )}
        </Card>
      )}

      {analysis.rescued.length > 0 && (
        <Card>
          <CardTitle>Gives these more to go with</CardTitle>
          <CardDescription className="mt-1">
            Pieces in fewer than two good outfits now that would reach two or
            more.
          </CardDescription>
          <ul className="mt-3 flex flex-col gap-2">
            {analysis.rescued.map((item) => (
              <li key={item.id}>
                <OwnedRow item={item} familyHex={familyHex} />
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}

function Fact({ term, value }: { term: string; value: string }) {
  return (
    <div>
      <dt className="text-ink-soft">{term}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

/** Good outfits now and with it, by occasion and season: a table, readable as it is. */
function Coverage({
  analysis,
  reference,
}: {
  analysis: Analysis;
  reference: Reference;
}) {
  const occasions = [...new Set(analysis.cells.map((c) => c.occasion_id))];
  const seasons = [...new Set(analysis.cells.map((c) => c.season))];
  const names = new Map(reference.occasions.map((o) => [o.id, o.name]));
  const seasonNames = new Map(reference.seasons.map((s) => [s.id, s.name]));
  const cell = new Map(
    analysis.cells.map((c) => [`${c.occasion_id}:${c.season}`, c]),
  );
  const shown = (n: number) => (n === 0 ? "None" : n >= 10 ? "10+" : String(n));

  return (
    <Card>
      <CardTitle>Where it adds outfits</CardTitle>
      <CardDescription className="mt-1">
        Good outfits now, and with it. Gaps (&ldquo;None&rdquo;) and thin spots
        count for most; past ten, more add nothing.
      </CardDescription>
      {/* relative: keeps the screen-reader text in the cells inside the scroll area. */}
      <div className="relative mt-4 overflow-x-auto">
        <table className="w-full min-w-[28rem] border-separate border-spacing-1 text-sm">
          <thead>
            <tr>
              <th scope="col" className="text-left font-medium text-ink-soft">
                <span className="sr-only">Occasion</span>
              </th>
              {seasons.map((season) => (
                <th
                  key={season}
                  scope="col"
                  className="font-medium text-ink-soft"
                >
                  {seasonNames.get(season) ?? season}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {occasions.map((occasion) => (
              <tr key={occasion}>
                <th scope="row" className="pr-2 text-left font-normal">
                  {names.get(occasion) ?? occasion}
                </th>
                {seasons.map((season) => {
                  const entry = cell.get(`${occasion}:${season}`);
                  const before = entry?.before ?? 0;
                  const after = before + (entry?.added ?? 0);
                  const grows = after > before && before < 10;
                  return (
                    <td
                      key={season}
                      className={cn(
                        "rounded-md px-2 py-2 text-center tabular-nums",
                        grows ? "bg-indigo/10 font-medium" : "bg-tile",
                      )}
                    >
                      {grows ? (
                        <>
                          {shown(before)} <span aria-hidden>→</span>
                          <span className="sr-only">to</span> {shown(after)}
                        </>
                      ) : (
                        shown(before)
                      )}
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

function PurchaseDialog({ candidate }: { candidate: Candidate }) {
  const router = useRouter();
  const purchase = usePurchase(candidate.id);
  const [open, setOpen] = useState(false);
  const [price, setPrice] = useState(paiseToRupeesText(candidate.price));
  const [day, setDay] = useState(todayIso());
  const [size, setSize] = useState(candidate.size_label ?? "");
  const [error, setError] = useState<string | null>(null);
  const [priceError, setPriceError] = useState<string | undefined>();

  async function confirm() {
    const paid = rupeesToPaise(price);
    if (paid !== null && (Number.isNaN(paid) || paid > MAX_RUPEES * 100)) {
      setPriceError(AMOUNT_ERROR);
      return;
    }
    setPriceError(undefined);
    setError(null);
    try {
      const made = await purchase.mutateAsync({
        price: paid,
        purchased_on: day || null,
        size_label: size.trim() || null,
      });
      setOpen(false);
      toast.success(`${candidate.display_name} added to your wardrobe`);
      router.push(`/wardrobe/${made.item_id}`);
    } catch (failure) {
      setError(problemFrom(failure).message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>I bought it</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add it to your wardrobe</DialogTitle>
          <DialogDescription>
            It becomes an item, with its photo, and suggestions start using it.
          </DialogDescription>
        </DialogHeader>
        {error && <Alert tone="error">{error}</Alert>}
        <Field label="Price paid, in rupees (optional)" error={priceError}>
          {(control) => (
            <Input
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              inputMode="decimal"
              autoComplete="off"
              {...control}
            />
          )}
        </Field>
        <Field label="Bought on">
          {(control) => (
            <Input
              type="date"
              value={day}
              max={todayIso()}
              onChange={(e) => setDay(e.target.value)}
              {...control}
            />
          )}
        </Field>
        <Field label="Size (optional)">
          {(control) => (
            <Input
              value={size}
              onChange={(e) => setSize(e.target.value)}
              maxLength={20}
              autoComplete="off"
              {...control}
            />
          )}
        </Field>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Cancel</Button>
          </DialogClose>
          <Button loading={purchase.isPending} onClick={() => void confirm()}>
            Add to wardrobe
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteDialog({ candidate }: { candidate: Candidate }) {
  const router = useRouter();
  const remove = useDeleteCandidate(candidate.id);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setError(null);
    try {
      await remove.mutateAsync();
      setOpen(false);
      router.replace("/shopping");
      toast.success(`${candidate.display_name} removed from your list`);
    } catch (failure) {
      setError(problemFrom(failure).message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="quiet">Delete</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remove {candidate.display_name}?</DialogTitle>
          <DialogDescription>
            It comes off your shopping list, with its photo. To keep it but set
            it aside, mark it Skipped instead.
          </DialogDescription>
        </DialogHeader>
        {error && <Alert tone="error">{error}</Alert>}
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            loading={remove.isPending}
            onClick={() => void confirm()}
          >
            Remove
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
