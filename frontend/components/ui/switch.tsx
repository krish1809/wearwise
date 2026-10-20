"use client";

import { Switch as SwitchPrimitive } from "radix-ui";
import * as React from "react";

import { cn, focusRing } from "@/lib/utils";

function Switch({
  className,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      className={cn(
        // A 40 by 24px track with a 44px-tall touch area.
        "relative inline-flex h-6 w-10 shrink-0 items-center rounded-full border-2 border-transparent transition-colors after:absolute after:-inset-x-1 after:-inset-y-2.5",
        "data-checked:bg-indigo data-unchecked:bg-ink-soft/60 hover:data-unchecked:bg-ink-soft/80",
        "disabled:cursor-not-allowed disabled:opacity-50",
        focusRing,
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb className="block size-5 rounded-full bg-on-ink transition-transform data-checked:translate-x-4 data-unchecked:translate-x-0" />
    </SwitchPrimitive.Root>
  );
}

export { Switch };
