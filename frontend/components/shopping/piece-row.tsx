import Link from "next/link";

import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { cn, focusRing } from "@/lib/utils";
import type { ItemBrief, PhotoRef } from "@/lib/wardrobe";

/** A small photo (or colour block), a name, and anything after it. */
export function PieceRow({
  name,
  photo,
  hex,
  imageUrl,
  href,
  label,
  children,
  className,
}: {
  name: string;
  /** Shown in place of the plain name (a button, say). */
  label?: React.ReactNode;
  photo?: PhotoRef | null;
  hex: string | null | undefined;
  imageUrl?: string | null;
  href?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full">
        <ItemPhoto photo={photo} alt="" hex={hex} imageUrl={imageUrl} />
      </span>
      {label ? (
        <span className="min-w-0 flex-1">{label}</span>
      ) : href ? (
        <Link
          href={href}
          className={cn(
            "min-w-0 flex-1 truncate rounded hover:underline",
            focusRing,
          )}
        >
          {name}
        </Link>
      ) : (
        <span className="min-w-0 flex-1 truncate">{name}</span>
      )}
      {children}
    </div>
  );
}

/** An owned item as a row that links to it. */
export function OwnedRow({
  item,
  familyHex,
  children,
}: {
  item: ItemBrief;
  familyHex: Map<string, string | null>;
  children?: React.ReactNode;
}) {
  return (
    <PieceRow
      name={item.display_name}
      photo={item.photo}
      hex={item.color_hex ?? familyHex.get(item.color_primary)}
      href={`/wardrobe/${item.id}`}
    >
      {children}
    </PieceRow>
  );
}
