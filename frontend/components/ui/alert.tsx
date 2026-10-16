import { CircleAlert, Info } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

type AlertProps = {
  tone?: "info" | "error";
  children: React.ReactNode;
  className?: string;
};

/** A message about the whole form or page. The icon carries the tone, so colour isn't the only signal. */
function Alert({ tone = "info", children, className }: AlertProps) {
  const Icon = tone === "error" ? CircleAlert : Info;
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      data-slot="alert"
      className={cn(
        "flex items-start gap-3 rounded-lg bg-surface p-4 text-sm text-ink",
        className,
      )}
    >
      <Icon
        aria-hidden
        className={cn(
          "mt-0.5 size-5 shrink-0",
          tone === "error" ? "text-skip" : "text-indigo",
        )}
      />
      <div>{children}</div>
    </div>
  );
}

export { Alert };
