import { cn } from "@/lib/utils";

// Multicolour has no single hex, so it gets a wheel of colours instead.
const MULTICOLOUR =
  "conic-gradient(#C0282D, #E07B2A, #C9A227, #2E7D4F, #1F2A44, #6B4A9E, #C0282D)";

type SwatchProps = {
  hex: string | null;
  className?: string;
};

/** A colour dot. Decorative: the colour's name is always written next to it. */
function Swatch({ hex, className }: SwatchProps) {
  return (
    <span
      aria-hidden
      data-slot="swatch"
      className={cn(
        // The border keeps white and cream visible on a white card.
        "inline-block size-4 shrink-0 rounded-full border border-line-strong",
        className,
      )}
      style={{ background: hex ?? MULTICOLOUR }}
    />
  );
}

export { Swatch };
