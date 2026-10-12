import { CircleAlert } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

type ErrorStateProps = {
  title: string;
  /** Say what went wrong and what to do about it. */
  children: React.ReactNode;
  /** Usually a "Try again" button. */
  action?: React.ReactNode;
  className?: string;
};

function ErrorState({ title, children, action, className }: ErrorStateProps) {
  return (
    <div
      role="alert"
      data-slot="error-state"
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl bg-surface px-6 py-12 text-center",
        className,
      )}
    >
      <CircleAlert aria-hidden className="size-8 text-skip" />
      <h2 className="font-display text-lg leading-tight font-semibold tracking-tight">
        {title}
      </h2>
      <div className="max-w-prose text-ink-soft">{children}</div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export { ErrorState };
