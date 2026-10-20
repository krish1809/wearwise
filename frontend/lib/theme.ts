"use client";

import { useCallback, useEffect, useState } from "react";

export type ThemeChoice = "system" | "light" | "dark";

const KEY = "wearwise-theme";

/**
 * Runs in the page head before anything paints, so a dark page never flashes light. Kept as a
 * string because it can't wait for the app's code to load.
 */
export const THEME_SCRIPT = `(function(){try{var p=localStorage.getItem("${KEY}")||"system";var d=p==="dark"||(p==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light";}catch(e){}})();`;

function stored(): ThemeChoice {
  try {
    const value = localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

function apply(choice: ThemeChoice) {
  const dark =
    choice === "dark" ||
    (choice === "system" &&
      window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

/** The person's theme: System follows the device, and follows it when it changes. */
export function useTheme(): [ThemeChoice, (choice: ThemeChoice) => void] {
  // Read once on the client; the menu that shows it only renders after it opens.
  const [choice, setChoice] = useState<ThemeChoice>(() =>
    typeof window === "undefined" ? "system" : stored(),
  );

  useEffect(() => {
    if (choice !== "system") return;
    const query = window.matchMedia?.("(prefers-color-scheme: dark)");
    const follow = () => apply("system");
    query?.addEventListener?.("change", follow);
    return () => query?.removeEventListener?.("change", follow);
  }, [choice]);

  const choose = useCallback((next: ThemeChoice) => {
    try {
      localStorage.setItem(KEY, next);
    } catch {
      // Private browsing: the choice lasts until the page is closed.
    }
    setChoice(next);
    apply(next);
  }, []);

  return [choice, choose];
}
