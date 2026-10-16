import * as React from "react";

import { cn } from "@/lib/utils";

// Depth comes from surface against paper, not from a shadow.
function Card({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card"
      className={cn("rounded-xl bg-surface p-4 sm:p-6", className)}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<"h3">) {
  return (
    <h3
      data-slot="card-title"
      className={cn("text-lg font-medium text-ink", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="card-description"
      className={cn("text-ink-soft", className)}
      {...props}
    />
  );
}

export { Card, CardDescription, CardTitle };
