"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { problemFrom } from "@/lib/api/errors";
import { cn, focusRing } from "@/lib/utils";
import { type Item, itemDetail, useItems, useSetLink } from "@/lib/wardrobe";

type SetPanelProps = {
  item: Item;
  colourNames: Map<string, string>;
  categoryNames: Map<string, string>;
};

/** The other pieces in the item's matching set, and adding or leaving one. */
export function SetPanel({ item, colourNames, categoryNames }: SetPanelProps) {
  const link = useSetLink(item.id);
  const [open, setOpen] = useState(false);

  async function change(otherId: string | null) {
    try {
      await link.mutateAsync(otherId);
      setOpen(false);
      toast.success(otherId ? "Added to the set" : "Taken out of the set");
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <div className="mt-4 flex flex-col gap-4">
      {item.set_members.length > 0 && (
        <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4">
          {item.set_members.map((member) => (
            <li key={member.id}>
              <Link
                href={`/wardrobe/${member.id}`}
                className={cn("group block rounded-lg", focusRing)}
              >
                <div className="flex aspect-3/4 items-center justify-center rounded-lg bg-tile p-2 *:max-h-full *:max-w-full group-hover:bg-line">
                  <ItemPhoto
                    photo={member.photo}
                    alt={`${member.display_name}, ${itemDetail(member, colourNames, categoryNames)}`}
                    hex={null}
                  />
                </div>
                <p className="mt-1 truncate text-sm">{member.display_name}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-3">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button variant="secondary">
              {item.set_members.length ? "Add another piece" : "Make a set"}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Pair with another item</DialogTitle>
              <DialogDescription>
                Choose the piece that goes with {item.display_name}.
              </DialogDescription>
            </DialogHeader>
            {open && (
              <ItemChooser
                exclude={[item.id, ...item.set_members.map((m) => m.id)]}
                colourNames={colourNames}
                categoryNames={categoryNames}
                busy={link.isPending}
                onChoose={(id) => void change(id)}
              />
            )}
          </DialogContent>
        </Dialog>
        {item.set_members.length > 0 && (
          <Button
            variant="quiet"
            loading={link.isPending && !open}
            onClick={() => void change(null)}
          >
            Take out of the set
          </Button>
        )}
      </div>
    </div>
  );
}

function ItemChooser({
  exclude,
  colourNames,
  categoryNames,
  busy,
  onChoose,
}: {
  exclude: string[];
  colourNames: Map<string, string>;
  categoryNames: Map<string, string>;
  busy: boolean;
  onChoose: (id: string) => void;
}) {
  const [q, setQ] = useState("");
  const items = useItems({
    q,
    group: [],
    color: [],
    season: [],
    occasion: [],
    style: [],
    status: [],
    archived: false,
    sort: "category",
  });
  const choices = (items.data?.pages ?? [])
    .flatMap((page) => page.items)
    .filter((candidate) => !exclude.includes(candidate.id));

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <div className="relative">
        <Search
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-ink-soft"
        />
        <Input
          type="search"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          aria-label="Search your wardrobe"
          placeholder="Search"
          className="pl-10"
        />
      </div>
      <ul className="flex max-h-80 flex-col gap-1 overflow-y-auto">
        {choices.map((choice) => (
          <li key={choice.id}>
            <button
              type="button"
              disabled={busy}
              onClick={() => onChoose(choice.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg p-2 text-left hover:bg-tile disabled:opacity-50",
                focusRing,
              )}
            >
              <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full">
                <ItemPhoto photo={choice.photo} alt="" hex={choice.color_hex} />
              </span>
              <span className="min-w-0">
                <span className="block truncate font-medium">
                  {choice.display_name}
                </span>
                <span className="block truncate text-sm text-ink-soft">
                  {itemDetail(choice, colourNames, categoryNames)}
                </span>
              </span>
            </button>
          </li>
        ))}
        {items.data && choices.length === 0 && (
          <li className="p-2 text-ink-soft">No other items match.</li>
        )}
      </ul>
      {items.hasNextPage && (
        <Button
          variant="quiet"
          loading={items.isFetchingNextPage}
          onClick={() => void items.fetchNextPage()}
        >
          Show more
        </Button>
      )}
    </div>
  );
}
