"use client";

import { Pencil } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { PageLoading } from "@/components/app-shell";
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
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { MarkWorn } from "@/components/outfits/mark-worn";
import { SetPanel } from "@/components/wardrobe/set-panel";
import { BackLink } from "@/components/wardrobe/wardrobe-data";
import { ApiRequestError, problemFrom } from "@/lib/api/errors";
import { dayPhrase, todayIso } from "@/lib/dates";
import { formatRupees } from "@/lib/money";
import { useOutfits } from "@/lib/outfits";
import { type Reference, useReference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";
import {
  type Category,
  type Item,
  itemDetail,
  useArchiveItem,
  useCategories,
  useDeleteItem,
  useItem,
  useUpdateItem,
} from "@/lib/wardrobe";

export function ItemView() {
  const { id } = useParams<{ id: string }>();
  const item = useItem(id);
  const reference = useReference();
  const categories = useCategories();

  if (
    item.error instanceof ApiRequestError &&
    item.error.problem.code === "item_not_found"
  ) {
    return (
      <EmptyState
        title="That item doesn't exist"
        action={
          <Button asChild variant="secondary">
            <Link href="/wardrobe">Back to your wardrobe</Link>
          </Button>
        }
      >
        It may have been deleted.
      </EmptyState>
    );
  }
  if (item.isError || reference.isError || categories.isError) {
    return (
      <ErrorState
        title="Couldn't load this item"
        action={
          <Button variant="secondary" onClick={() => void item.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!item.data || !reference.data || !categories.data) return <PageLoading />;

  return (
    <ItemDetails
      item={item.data}
      reference={reference.data}
      categories={categories.data}
    />
  );
}

function ItemDetails({
  item,
  reference,
  categories,
}: {
  item: Item;
  reference: Reference;
  categories: Category[];
}) {
  const update = useUpdateItem(item.id);
  const archive = useArchiveItem(item.id);
  const colourNames = new Map(
    reference.color_families.map((c) => [c.id, c.name]),
  );
  const categoryNames = new Map(categories.map((c) => [c.id, c.name]));
  const name = (list: { id: string; name: string }[], id: string | null) =>
    list.find((entry) => entry.id === id)?.name ?? id;
  const detail = itemDetail(item, colourNames, categoryNames);
  const hex =
    item.color_hex ??
    reference.color_families.find((c) => c.id === item.color_primary)?.hex;

  const facts: [string, string | null][] = [
    ["Brand", item.brand],
    ["Size", item.size_label],
    [
      "Second colour",
      item.color_secondary
        ? (colourNames.get(item.color_secondary) ?? null)
        : null,
    ],
    ["Pattern", name(reference.patterns, item.pattern)],
    ["Fabric", item.fabric ? name(reference.fabrics, item.fabric) : null],
    ["Fit", item.fit ? name(reference.fits, item.fit) : null],
    ["Formality", name(reference.formality_levels, String(item.formality))],
    [
      "Seasons",
      item.seasons.length
        ? item.seasons.map((s) => name(reference.seasons, s)).join(", ")
        : "Any season",
    ],
    [
      "Occasions",
      item.occasion_ids.map((o) => name(reference.occasions, o)).join(", ") ||
        null,
    ],
    [
      "Style",
      item.style_tags
        .map((t) => name(reference.style_profiles, t))
        .join(", ") || null,
    ],
    ["Price", item.price !== null ? formatRupees(item.price) : null],
    [
      "Bought",
      item.purchased_on
        ? new Date(`${item.purchased_on}T00:00:00`).toLocaleDateString(
            "en-IN",
            {
              day: "numeric",
              month: "long",
              year: "numeric",
            },
          )
        : null,
    ],
    [
      "Wash after",
      item.wears_before_wash === null
        ? "Not on a schedule"
        : item.wears_before_wash === 1
          ? "Every wear"
          : `${item.wears_before_wash} wears`,
    ],
    ["Notes", item.notes],
  ];

  // Outfits are built from clothes, shoes, and accessories; fragrance and grooming ride along.
  const role = reference.slots.find((slot) => slot.id === item.slot)?.role;
  const wearable = role === "core" || role === "accessory";

  async function changeStatus(status: string) {
    try {
      await update.mutateAsync({ status });
      toast.success(
        `Marked as ${name(reference.statuses, status)?.toLowerCase()}`,
      );
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  async function toggleArchive(archived = !item.archived) {
    try {
      await archive.mutateAsync(archived);
      if (archived) {
        // Archiving hides it everywhere, so it can be taken back straight away.
        toast.success("Archived", {
          action: { label: "Undo", onClick: () => void toggleArchive(false) },
        });
      } else {
        toast.success("Back in your wardrobe");
      }
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/wardrobe">Wardrobe</BackLink>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <div className="flex aspect-3/4 items-center justify-center rounded-xl bg-tile p-6 *:max-h-full *:max-w-full">
          <ItemPhoto
            photo={item.photo}
            alt={`${item.display_name}, ${detail}`}
            hex={hex}
            size="full"
          />
        </div>
        <div className="flex min-w-0 flex-col gap-6">
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight break-words">
              {item.display_name}
            </h1>
            <p className="mt-1 text-ink-soft">{detail}</p>
          </div>
          {item.archived && (
            <Alert>
              Archived: hidden from your wardrobe. Restore it to use it again.
            </Alert>
          )}
          <Field label="Status" className="max-w-xs">
            {(control) => (
              <Select
                value={item.status}
                disabled={update.isPending}
                onChange={(event) => void changeStatus(event.target.value)}
                {...control}
              >
                {reference.statuses.map((status) => (
                  <option key={status.id} value={status.id}>
                    {status.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link href={`/wardrobe/${item.id}/edit`}>
                <Pencil aria-hidden />
                Edit
              </Link>
            </Button>
            {!item.archived && wearable && (
              <Button asChild variant="secondary">
                <Link href={`/outfits/suggest?with=${item.id}`}>
                  What goes with this?
                </Link>
              </Button>
            )}
            <Button
              variant="secondary"
              loading={archive.isPending}
              onClick={() => void toggleArchive()}
            >
              {item.archived ? "Restore" : "Archive"}
            </Button>
            <DeleteItem item={item} />
          </div>
          <dl className="flex flex-col gap-3">
            {facts
              .filter(([, value]) => value)
              .map(([label, value]) => (
                <div
                  key={label}
                  className="flex flex-col gap-0.5 sm:flex-row sm:gap-6"
                >
                  <dt className="w-32 shrink-0 text-ink-soft">{label}</dt>
                  <dd className="break-words whitespace-pre-line">{value}</dd>
                </div>
              ))}
          </dl>
          <WearCard item={item} />
          <ItemOutfits itemId={item.id} />
          <Card>
            <CardTitle>Matching set</CardTitle>
            <CardDescription className="mt-1">
              Link pieces that belong together, like a suit&apos;s jacket and
              trousers.
            </CardDescription>
            <SetPanel
              item={item}
              colourNames={colourNames}
              categoryNames={categoryNames}
            />
          </Card>
        </div>
      </div>
    </div>
  );
}

function DeleteItem({ item }: { item: Item }) {
  const router = useRouter();
  const remove = useDeleteItem(item.id);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setError(null);
    try {
      await remove.mutateAsync();
      setOpen(false);
      router.replace("/wardrobe");
      toast.success(`${item.display_name} deleted`);
    } catch (failure) {
      setError(problemFrom(failure).message);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setError(null);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="quiet">Delete</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {item.display_name}?</DialogTitle>
          <DialogDescription>
            The item and its photo are deleted for good. To keep it but hide it,
            archive it instead.
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
            Delete item
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function WearCard({ item }: { item: Item }) {
  const wash =
    item.wears_before_wash === null
      ? null
      : item.wears_since_wash >= item.wears_before_wash
        ? "Due a wash."
        : `${item.wears_since_wash} of ${item.wears_before_wash} ${item.wears_before_wash === 1 ? "wear" : "wears"} before a wash.`;
  return (
    <Card className="flex flex-col gap-4">
      <div>
        <CardTitle>Wear</CardTitle>
        <CardDescription className="mt-1">
          {item.wear_count && item.last_worn_on
            ? `Worn ${item.wear_count} ${item.wear_count === 1 ? "time" : "times"}, last ${dayPhrase(item.last_worn_on)}.`
            : "Not worn yet."}{" "}
          {wash}
        </CardDescription>
      </div>
      {!item.archived && (
        <MarkWorn
          what={{ item_ids: [item.id] }}
          wornToday={item.last_worn_on === todayIso()}
        />
      )}
      <Link
        href="/worn"
        className={cn(
          "self-start rounded text-sm font-medium text-indigo underline underline-offset-4",
          focusRing,
        )}
      >
        See the wear log
      </Link>
    </Card>
  );
}

function ItemOutfits({ itemId }: { itemId: string }) {
  const outfits = useOutfits({ favorite: false, itemId });
  const found = (outfits.data?.pages ?? []).flatMap((page) => page.outfits);
  if (found.length === 0) return null;
  return (
    <Card>
      <CardTitle>In your outfits</CardTitle>
      <ul className="mt-3 flex flex-col gap-1">
        {found.map((outfit) => (
          <li key={outfit.id}>
            <Link
              href={`/outfits/${outfit.id}`}
              className={cn(
                "block truncate rounded py-1.5 font-medium hover:underline",
                focusRing,
              )}
            >
              {outfit.display_name}
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}
