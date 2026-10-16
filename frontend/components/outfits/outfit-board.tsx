import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { cn } from "@/lib/utils";
import type { PhotoRef } from "@/lib/wardrobe";

/** One piece on the board: an item, or a deleted item's name. */
export type BoardPiece = {
  slot: string;
  name: string;
  removed: boolean;
  item: {
    color_primary: string;
    color_hex: string | null;
    photo: PhotoRef | null;
  } | null;
};

type SlotInfo = { id: string; role: string; position: number };

type OutfitBoardProps = {
  pieces: BoardPiece[];
  /** Slot roles and order, from the reference data. */
  slots: SlotInfo[];
  /** Colour family id to its hex, for pieces without a photo or a measured colour. */
  familyHex: Map<string, string | null>;
  size?: "large" | "small";
  /** Inside a link that already names the outfit, the board is decoration. */
  decorative?: boolean;
  className?: string;
};

// The design lays the layer beside the top, with the accessories.
const BESIDE = new Set(["layer"]);

/**
 * The outfit as a flat lay: core pieces down the left (top or one-piece, bottom, footwear),
 * the layer and accessories down the right, on one backdrop. Positions follow the slot, so
 * every outfit reads the same way at a glance.
 */
export function OutfitBoard({
  pieces,
  slots,
  familyHex,
  size = "large",
  decorative = false,
  className,
}: OutfitBoardProps) {
  const info = new Map(slots.map((slot) => [slot.id, slot]));
  const ordered = [...pieces].sort(
    (a, b) =>
      (info.get(a.slot)?.position ?? 99) - (info.get(b.slot)?.position ?? 99),
  );
  const main = ordered.filter(
    (p) => info.get(p.slot)?.role === "core" && !BESIDE.has(p.slot),
  );
  const side = ordered.filter((p) => !main.includes(p));
  const large = size === "large";

  return (
    <div
      data-slot="outfit-board"
      aria-hidden={decorative || undefined}
      className={cn(
        "grid grid-cols-[3fr_2fr] gap-3 rounded-xl bg-tile",
        large ? "p-4 sm:p-6" : "p-3",
        className,
      )}
    >
      <ul aria-label="Main pieces" className="flex flex-col gap-3">
        {main.map((piece) => (
          <Laid
            key={piece.slot}
            piece={piece}
            familyHex={familyHex}
            large={large}
            main
          />
        ))}
      </ul>
      <ul aria-label="Layer and accessories" className="flex flex-col gap-3">
        {side.map((piece) => (
          <Laid
            key={piece.slot}
            piece={piece}
            familyHex={familyHex}
            large={large}
          />
        ))}
      </ul>
    </div>
  );
}

function Laid({
  piece,
  familyHex,
  large,
  main = false,
}: {
  piece: BoardPiece;
  familyHex: Map<string, string | null>;
  large: boolean;
  main?: boolean;
}) {
  const hex = piece.item
    ? (piece.item.color_hex ?? familyHex.get(piece.item.color_primary) ?? null)
    : null;
  return (
    <li className="min-w-0">
      <div
        className={cn(
          "flex items-center justify-center *:max-h-full *:max-w-full",
          main ? "aspect-[4/3]" : "aspect-square",
          piece.removed &&
            "rounded-lg border-2 border-dashed border-line-strong",
        )}
      >
        {piece.removed ? (
          <span className="px-2 text-center text-sm text-ink-soft">
            Removed
          </span>
        ) : (
          <ItemPhoto
            photo={piece.item?.photo}
            alt={piece.name}
            hex={hex}
            className={piece.item?.photo ? "rounded-md" : undefined}
          />
        )}
      </div>
      {large && (
        <p
          className={cn(
            "mt-1 truncate text-sm",
            piece.removed ? "text-ink-soft line-through" : "text-ink",
          )}
        >
          {piece.name}
        </p>
      )}
    </li>
  );
}

/** Small squares of the outfit's actual colours, under the board. */
export function SwatchStrip({
  pieces,
  familyHex,
}: {
  pieces: BoardPiece[];
  familyHex: Map<string, string | null>;
}) {
  const colours = pieces
    .filter((piece) => piece.item)
    .map((piece) =>
      piece.item
        ? (piece.item.color_hex ??
          familyHex.get(piece.item.color_primary) ??
          null)
        : null,
    )
    .filter((hex): hex is string => Boolean(hex));
  if (colours.length === 0) return null;
  return (
    <div aria-hidden className="flex flex-wrap gap-1">
      {colours.map((hex, index) => (
        <span
          key={`${hex}-${index}`}
          className="size-3.5 rounded-sm border border-line-strong/40"
          style={{ background: hex }}
        />
      ))}
    </div>
  );
}
