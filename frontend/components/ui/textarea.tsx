import * as React from "react";

import { controlClasses } from "@/components/ui/input";
import { cn } from "@/lib/utils";

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        controlClasses,
        "h-auto min-h-24 py-2.5 placeholder:text-ink-soft",
        className,
      )}
      {...props}
    />
  );
}

export { Textarea };
