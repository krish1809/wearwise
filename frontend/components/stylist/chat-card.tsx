"use client";

import { Check, X } from "lucide-react";
import Link from "next/link";

import { OutfitBoard } from "@/components/outfits/outfit-board";
import { PieceRow } from "@/components/shopping/piece-row";
import { ShopPanel } from "@/components/shopping/shop-panel";
import { VerdictBadge } from "@/components/shopping/verdict-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { problemFrom } from "@/lib/api/errors";
import type { Reference } from "@/lib/profile";
import { type ChatAction, type ChatCard, useDecide } from "@/lib/stylist";
import { cn, focusRing } from "@/lib/utils";

/** One card in a reply: the app's own components, showing real rows by id. */
export function ChatCardView({
  card,
  reference,
  threadId,
}: {
  card: ChatCard;
  reference: Reference;
  threadId: string | null;
}) {
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));

  if (card.removed && card.type !== "outfit") {
    return (
      <p className="rounded-lg bg-tile px-3 py-2 text-sm text-ink-soft">
        No longer in your wardrobe or list.
      </p>
    );
  }
  if (card.type === "outfit") {
    return (
      <div className="max-w-sm">
        <OutfitBoard
          size="small"
          slots={slots}
          familyHex={familyHex}
          pieces={card.items.map((item) => ({
            slot: item.slot,
            name: item.display_name,
            removed: false,
            item,
          }))}
        />
        <p className="mt-1 text-sm text-ink-soft">
          {card.items.map((item) => item.display_name).join(", ")}
          {card.removed && " (a piece has since been removed)"}
        </p>
      </div>
    );
  }
  if (card.type === "item" && card.items[0]) {
    const item = card.items[0];
    return (
      <PieceRow
        className="max-w-sm"
        name={item.display_name}
        photo={item.photo}
        hex={item.color_hex ?? familyHex.get(item.color_primary)}
        href={`/wardrobe/${item.id}`}
      />
    );
  }
  if (card.type === "candidate" && card.candidate) {
    const candidate = card.candidate;
    return (
      <PieceRow
        className="max-w-sm"
        name={candidate.display_name}
        photo={candidate.photo}
        imageUrl={candidate.image_url}
        hex={candidate.color_hex ?? familyHex.get(candidate.color_primary)}
        href={`/shopping/${candidate.id}`}
      >
        <VerdictBadge verdict={candidate.verdict} />
      </PieceRow>
    );
  }
  if (card.type === "staple" && card.staple) {
    const staple = card.staple;
    return (
      <PieceRow className="max-w-sm" name={staple.name} hex={staple.hex}>
        <ShopPanel
          target={{ archetypeId: staple.id }}
          name={staple.name}
          trigger={<Button variant="quiet">Find it</Button>}
        />
      </PieceRow>
    );
  }
  if (card.type === "action" && card.action) {
    return (
      <ActionCard
        action={card.action}
        threadId={threadId}
        familyHex={familyHex}
      />
    );
  }
  return null;
}

const DONE_LINKS: Record<
  string,
  (result: Record<string, string>) => [string, string]
> = {
  save_outfit: (r) => [`/outfits/${r.outfit_id}`, "See the outfit"],
  plan_outfit: () => ["/week", "See My Week"],
  add_to_list: (r) => [`/shopping/${r.candidate_id}`, "See it on your list"],
  log_wear: () => ["/worn", "See the wear log"],
};

function ActionCard({
  action,
  threadId,
  familyHex,
}: {
  action: ChatAction;
  threadId: string | null;
  familyHex: Map<string, string | null>;
}) {
  const decide = useDecide(threadId);

  async function choose(confirm: boolean) {
    try {
      await decide.mutateAsync({ id: action.id, confirm });
      if (confirm) toast.success("Done");
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  const link = DONE_LINKS[action.kind]?.(action.result);
  return (
    <div className="max-w-md rounded-xl border border-line-strong/60 bg-surface p-4">
      <p className="text-sm font-medium">{action.summary}</p>
      {action.items.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-2">
          {action.items.map((item) => (
            <li
              key={item.id}
              className="flex size-12 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full"
            >
              <ItemPhoto
                photo={item.photo}
                alt={item.display_name}
                hex={item.color_hex ?? familyHex.get(item.color_primary)}
              />
            </li>
          ))}
        </ul>
      )}
      {action.status === "pending" ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button loading={decide.isPending} onClick={() => void choose(true)}>
            Confirm
          </Button>
          <Button
            variant="secondary"
            disabled={decide.isPending}
            onClick={() => void choose(false)}
          >
            Not now
          </Button>
        </div>
      ) : action.status === "done" ? (
        <p className="mt-3 flex items-center gap-1.5 text-sm">
          <Check aria-hidden className="size-4 text-buy" />
          Done.
          {link && (
            <Link
              href={link[0]}
              className={cn(
                "ml-1 text-indigo underline underline-offset-4",
                focusRing,
              )}
            >
              {link[1]}
            </Link>
          )}
        </p>
      ) : (
        <p className="mt-3 flex items-center gap-1.5 text-sm text-ink-soft">
          <X aria-hidden className="size-4" />
          Not done.
        </p>
      )}
    </div>
  );
}

export function Unavailable({ message }: { message: string }) {
  return <Alert>{message}</Alert>;
}
