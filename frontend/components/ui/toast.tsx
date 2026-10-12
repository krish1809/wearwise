"use client";

import {
  CircleAlert,
  CircleCheck,
  Info,
  LoaderCircle,
  TriangleAlert,
} from "lucide-react";
import { Toaster as Sonner, toast } from "sonner";

// Toasts are system messages: a white card, with the verdict colours only on the icon.
function Toaster() {
  return (
    <Sonner
      theme="light"
      position="bottom-center"
      icons={{
        success: <CircleCheck className="size-5 text-buy" />,
        error: <CircleAlert className="size-5 text-skip" />,
        warning: <TriangleAlert className="size-5 text-consider" />,
        info: <Info className="size-5 text-indigo" />,
        loading: <LoaderCircle className="size-5 animate-spin text-ink-soft" />,
      }}
      toastOptions={{
        unstyled: true,
        classNames: {
          toast:
            "flex w-full items-start gap-3 rounded-lg border border-line bg-surface p-4 text-base text-ink shadow-float",
          title: "font-medium",
          description: "text-sm text-ink-soft",
          actionButton:
            "ml-auto min-h-9 shrink-0 rounded-lg bg-ink px-3 text-sm font-medium text-white",
          cancelButton:
            "ml-auto min-h-9 shrink-0 rounded-lg px-3 text-sm font-medium text-ink",
        },
      }}
    />
  );
}

export { toast, Toaster };
