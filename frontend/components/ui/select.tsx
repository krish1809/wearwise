import { ChevronDownIcon } from "lucide-react";
import * as React from "react";

import { controlClasses } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/**
 * A native select with WearWise styling. Phones open their own picker, it works without
 * JavaScript, and screen readers know it. For a placeholder, start with
 * <option value="">Choose a fit</option>; it shows in the secondary text colour.
 */
function Select({
  className,
  children,
  ...props
}: React.ComponentProps<"select">) {
  return (
    <div data-slot="select" className={cn("relative", className)}>
      <select
        className={cn(
          controlClasses,
          "appearance-none pr-10 has-[option[value='']:checked]:text-ink-soft [&>option]:text-ink",
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDownIcon
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-3 size-5 -translate-y-1/2 text-ink-soft"
      />
    </div>
  );
}

export { Select };
