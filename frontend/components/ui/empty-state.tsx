import * as React from "react";

import { cn } from "@/lib/utils";

type EmptyStateProps = {
  icon?: React.ReactNode;
  title: string;
  /** Tell the person what to do next. */
  children: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
};

function EmptyState({
  icon,
  title,
  children,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl bg-surface px-6 py-12 text-center",
        className,
      )}
    >
      {icon && (
        <div aria-hidden className="text-ink-soft [&_svg]:size-8">
          {icon}
        </div>
      )}
      <h2 className="font-display text-lg leading-tight font-semibold tracking-tight">
        {title}
      </h2>
      <div className="max-w-prose text-ink-soft">{children}</div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export { EmptyState };
