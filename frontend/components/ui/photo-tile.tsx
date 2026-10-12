import Link from "next/link";
import * as React from "react";

import { cn, focusRing } from "@/lib/utils";

type PhotoTileProps = Omit<React.HTMLAttributes<HTMLElement>, "children"> & {
  name: string;
  /** One short line under the name, such as the colour and category. */
  detail?: string;
  /** Makes the whole tile a link. */
  href?: string;
  /** The photo. It is fitted inside the tile with padding, so it never touches the edge. */
  children: React.ReactNode;
  className?: string;
};

/** A garment on the studio backdrop: a 3:4 tile, photo first, then one line of text. */
function PhotoTile({
  name,
  detail,
  href,
  children,
  className,
  ...props
}: PhotoTileProps) {
  const body = (
    <>
      <div className="flex aspect-3/4 items-center justify-center overflow-hidden rounded-xl bg-tile p-4 transition-colors *:max-h-full *:max-w-full *:object-contain group-hover:bg-line">
        {children}
      </div>
      <div className="mt-2 min-w-0">
        <p className="truncate text-sm font-medium text-ink">{name}</p>
        {detail && <p className="truncate text-sm text-ink-soft">{detail}</p>}
      </div>
    </>
  );

  if (href) {
    return (
      <Link
        href={href}
        data-slot="photo-tile"
        className={cn("group block rounded-xl", focusRing, className)}
        {...props}
      >
        {body}
      </Link>
    );
  }

  return (
    <div data-slot="photo-tile" className={className} {...props}>
      {body}
    </div>
  );
}

export { PhotoTile };
