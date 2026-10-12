import * as React from "react";

import { cn } from "@/lib/utils";

/** A placeholder in the shape of content that is still loading. */
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      aria-hidden
      data-slot="skeleton"
      className={cn("rounded-lg bg-tile motion-safe:animate-pulse", className)}
      {...props}
    />
  );
}

/** A loading photo tile, the same shape as the real one. */
function PhotoTileSkeleton({ className }: { className?: string }) {
  return (
    <div aria-hidden className={className}>
      <Skeleton className="aspect-3/4 rounded-xl" />
      <Skeleton className="mt-2 h-4 w-3/4" />
      <Skeleton className="mt-1.5 h-4 w-1/2" />
    </div>
  );
}

export { PhotoTileSkeleton, Skeleton };
