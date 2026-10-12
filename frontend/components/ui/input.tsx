import * as React from "react";

import { cn, focusRing } from "@/lib/utils";

// Shared by text inputs and select triggers, so every form control has the same frame.
const controlClasses = cn(
  "h-11 w-full min-w-0 rounded-lg border border-line bg-surface px-3 text-base text-ink transition-colors",
  "hover:border-ink-soft aria-invalid:border-skip",
  "disabled:cursor-not-allowed disabled:border-line disabled:bg-tile disabled:text-ink-soft",
  focusRing,
);

function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      data-slot="input"
      className={cn(controlClasses, "placeholder:text-ink-soft", className)}
      {...props}
    />
  );
}

export { controlClasses, Input };
