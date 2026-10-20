"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useRef, useState } from "react";

import { cn } from "@/lib/utils";

// How far a finger has to travel, and how much more sideways than up or down.
const COMMIT = 96;
const SIDEWAYS = 1.5;

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches)
  );
}

/**
 * Swipe right to like, left to dislike, with a finger (a mouse uses the buttons). Vertical
 * scrolling is left alone. The board follows the finger, unless the person asks for reduced
 * motion: then nothing moves, and only the label shows which way it will go.
 */
export function Swipeable({
  onLike,
  onDislike,
  label,
  children,
}: {
  onLike: () => void;
  onDislike: () => void;
  /** Read out with the instructions, such as the outfit's name. */
  label: string;
  children: React.ReactNode;
}) {
  const start = useRef<{ x: number; y: number; id: number } | null>(null);
  const [dx, setDx] = useState(0);
  const [still, setStill] = useState(false);

  function reset() {
    start.current = null;
    setDx(0);
  }

  return (
    <div
      className="relative touch-pan-y select-none"
      aria-label={`${label}. On a touch screen, swipe right to like or left to dislike.`}
      role="group"
      onPointerDown={(event) => {
        if (event.pointerType !== "touch" && event.pointerType !== "pen")
          return;
        setStill(prefersReducedMotion());
        start.current = {
          x: event.clientX,
          y: event.clientY,
          id: event.pointerId,
        };
      }}
      onPointerMove={(event) => {
        const from = start.current;
        if (!from || from.id !== event.pointerId) return;
        const x = event.clientX - from.x;
        const y = event.clientY - from.y;
        if (Math.abs(x) < Math.abs(y) * SIDEWAYS) {
          setDx(0);
          return;
        }
        setDx(x);
      }}
      onPointerUp={() => {
        if (dx >= COMMIT) onLike();
        else if (dx <= -COMMIT) onDislike();
        reset();
      }}
      onPointerCancel={reset}
    >
      <div
        className={cn(dx === 0 && "motion-safe:transition-transform")}
        style={
          still || dx === 0
            ? undefined
            : { transform: `translateX(${dx}px) rotate(${dx / 40}deg)` }
        }
      >
        {children}
      </div>
      {Math.abs(dx) >= 24 && (
        <span
          aria-hidden
          className={cn(
            "pointer-events-none absolute top-4 flex items-center gap-1.5 rounded-full bg-surface px-3 py-1.5 font-medium shadow-float",
            dx > 0 ? "left-4 text-buy" : "right-4 text-skip",
            Math.abs(dx) < COMMIT && "opacity-60",
          )}
        >
          {dx > 0 ? (
            <ThumbsUp aria-hidden className="size-5" />
          ) : (
            <ThumbsDown aria-hidden className="size-5" />
          )}
          {dx > 0 ? "Like" : "Dislike"}
        </span>
      )}
    </div>
  );
}
