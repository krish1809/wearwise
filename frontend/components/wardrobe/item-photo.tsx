import { cn } from "@/lib/utils";
import type { PhotoRef } from "@/lib/wardrobe";

type ItemPhotoProps = {
  photo: PhotoRef | null | undefined;
  /** Built from the item's name, colour, and category. */
  alt: string;
  /** Shown as a plain colour block when there's no photo. */
  hex: string | null | undefined;
  /** A shop's own picture (a shopping candidate), used when there's no photo. */
  imageUrl?: string | null;
  size?: "thumb" | "full";
  className?: string;
};

/**
 * The item's photo, or, without one, a block of its colour so the grid still reads by colour.
 * Photos come from the API, which checks they belong to the person.
 */
export function ItemPhoto({
  photo,
  alt,
  hex,
  imageUrl,
  size = "thumb",
  className,
}: ItemPhotoProps) {
  if (photo) {
    return (
      // A private photo behind the login, so it can't go through Next's image optimiser.
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={size === "thumb" ? photo.thumb_url : photo.url}
        alt={alt}
        width={photo.width}
        height={photo.height}
        loading={size === "thumb" ? "lazy" : "eager"}
        decoding="async"
        className={cn("h-auto object-contain", className)}
      />
    );
  }
  if (imageUrl) {
    return (
      // A shop's picture, loaded from the shop without saying which page it's on.
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={imageUrl}
        alt={alt}
        referrerPolicy="no-referrer"
        loading={size === "thumb" ? "lazy" : "eager"}
        decoding="async"
        className={cn("h-auto object-contain", className)}
      />
    );
  }
  return (
    <div
      role="img"
      aria-label={`${alt}, no photo`}
      className={cn(
        "aspect-square w-3/5 rounded-xl border border-line-strong/40",
        className,
      )}
      style={{ background: hex ?? "var(--color-line)" }}
    />
  );
}
