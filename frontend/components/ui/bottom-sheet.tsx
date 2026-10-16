"use client";

import * as React from "react";
import { Drawer as DrawerPrimitive } from "vaul";

import { cn } from "@/lib/utils";

// A panel that slides up from the bottom on phones, used where desktop shows a side rail.

function BottomSheet(props: React.ComponentProps<typeof DrawerPrimitive.Root>) {
  return <DrawerPrimitive.Root data-slot="bottom-sheet" {...props} />;
}

function BottomSheetTrigger(
  props: React.ComponentProps<typeof DrawerPrimitive.Trigger>,
) {
  return (
    <DrawerPrimitive.Trigger data-slot="bottom-sheet-trigger" {...props} />
  );
}

function BottomSheetClose(
  props: React.ComponentProps<typeof DrawerPrimitive.Close>,
) {
  return <DrawerPrimitive.Close data-slot="bottom-sheet-close" {...props} />;
}

function BottomSheetContent({
  className,
  children,
  ...props
}: React.ComponentProps<typeof DrawerPrimitive.Content>) {
  return (
    <DrawerPrimitive.Portal>
      <DrawerPrimitive.Overlay
        data-slot="bottom-sheet-overlay"
        className="fixed inset-0 z-50 bg-ink/40"
      />
      <DrawerPrimitive.Content
        data-slot="bottom-sheet-content"
        className={cn(
          "fixed inset-x-0 bottom-0 z-50 flex max-h-[85dvh] flex-col rounded-t-xl bg-surface pb-[env(safe-area-inset-bottom)] text-ink shadow-float",
          className,
        )}
        {...props}
      >
        <div
          aria-hidden
          className="mx-auto mt-3 h-1.5 w-12 shrink-0 rounded-full bg-line"
        />
        {children}
      </DrawerPrimitive.Content>
    </DrawerPrimitive.Portal>
  );
}

function BottomSheetHeader({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="bottom-sheet-header"
      className={cn("flex flex-col gap-1 px-4 pt-4", className)}
      {...props}
    />
  );
}

function BottomSheetTitle({
  className,
  ...props
}: React.ComponentProps<typeof DrawerPrimitive.Title>) {
  return (
    <DrawerPrimitive.Title
      data-slot="bottom-sheet-title"
      className={cn(
        "font-display text-lg leading-tight font-semibold tracking-tight",
        className,
      )}
      {...props}
    />
  );
}

function BottomSheetDescription({
  className,
  ...props
}: React.ComponentProps<typeof DrawerPrimitive.Description>) {
  return (
    <DrawerPrimitive.Description
      data-slot="bottom-sheet-description"
      className={cn("text-ink-soft", className)}
      {...props}
    />
  );
}

function BottomSheetFooter({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="bottom-sheet-footer"
      className={cn("mt-auto flex flex-col gap-3 p-4", className)}
      {...props}
    />
  );
}

export {
  BottomSheet,
  BottomSheetClose,
  BottomSheetContent,
  BottomSheetDescription,
  BottomSheetFooter,
  BottomSheetHeader,
  BottomSheetTitle,
  BottomSheetTrigger,
};
