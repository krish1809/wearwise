"use client";

import { useQuery } from "@tanstack/react-query";
import { CornerDownLeft, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useId,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { useAIStatus } from "@/lib/stylist";
import { cn } from "@/lib/utils";

type Entry = {
  id: string;
  label: string;
  group: "Go to" | "Do" | "Your items";
  href: string;
  // Other words people might type for it.
  also?: string;
};

const ENTRIES: Entry[] = [
  { id: "home", label: "Home", group: "Go to", href: "/home", also: "today" },
  {
    id: "wardrobe",
    label: "Wardrobe",
    group: "Go to",
    href: "/wardrobe",
    also: "clothes items",
  },
  {
    id: "outfits",
    label: "Outfits",
    group: "Go to",
    href: "/outfits",
    also: "saved",
  },
  {
    id: "week",
    label: "My Week",
    group: "Go to",
    href: "/week",
    also: "plan calendar weather",
  },
  {
    id: "laundry",
    label: "Laundry",
    group: "Go to",
    href: "/laundry",
    also: "wash clean",
  },
  {
    id: "trips",
    label: "Trips",
    group: "Go to",
    href: "/trips",
    also: "packing travel",
  },
  {
    id: "shopping",
    label: "Shopping",
    group: "Go to",
    href: "/shopping",
    also: "buy wishlist list",
  },
  {
    id: "picks",
    label: "Weekly picks",
    group: "Go to",
    href: "/picks",
    also: "trends fashion buy this week",
  },
  {
    id: "insights",
    label: "Insights",
    group: "Go to",
    href: "/insights",
    also: "stats worn cost",
  },
  {
    id: "guide",
    label: "Style Guide",
    group: "Go to",
    href: "/guide",
    also: "fabrics colours brands",
  },
  {
    id: "stylist",
    label: "Stylist",
    group: "Go to",
    href: "/stylist",
    also: "chat ask",
  },
  {
    id: "settings",
    label: "Settings",
    group: "Go to",
    href: "/settings",
    also: "profile account sizes",
  },
  {
    id: "add-item",
    label: "Add an item",
    group: "Do",
    href: "/wardrobe/new",
    also: "new clothes photo",
  },
  {
    id: "suggest",
    label: "Suggest an outfit",
    group: "Do",
    href: "/outfits/suggest",
    also: "what to wear",
  },
  {
    id: "build",
    label: "Build an outfit",
    group: "Do",
    href: "/outfits/new",
    also: "studio",
  },
  {
    id: "worn",
    label: "Log what I wore",
    group: "Do",
    href: "/worn/new",
    also: "wear",
  },
  {
    id: "remix",
    label: "Remix ten pieces",
    group: "Do",
    href: "/outfits/remix",
    also: "capsule",
  },
  {
    id: "add-candidate",
    label: "Add something to buy",
    group: "Do",
    href: "/shopping/new",
    also: "link shop",
  },
  {
    id: "plan",
    label: "Plan a starter wardrobe",
    group: "Do",
    href: "/shopping/plan",
    also: "capsule budget",
  },
];

// The device doesn't change while the page is open.
const noChanges = () => () => {};

function matches(entry: Entry, words: string[]): boolean {
  const text = `${entry.label} ${entry.also ?? ""}`.toLowerCase();
  return words.every((word) => text.includes(word));
}

/** Ctrl or Cmd + K, or the search button: jump to any page, action, or item by typing. */
export function QuickJump() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const mac = useSyncExternalStore(
    noChanges,
    () => /Mac|iPhone|iPad/.test(navigator.userAgent),
    () => false,
  );
  const status = useAIStatus();
  const listId = useId();

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((current) => !current);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const items = useQuery({
    queryKey: ["items", "jump", query.trim()],
    enabled: open && query.trim().length >= 2,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/items", {
        params: { query: { q: query.trim(), limit: 5 } },
      });
      return data?.items ?? [];
    },
  });

  const results = useMemo(() => {
    const aiOn = status.data !== undefined && status.data.reason !== "off";
    const fixed = ENTRIES.filter(
      (entry) => (entry.id !== "stylist" || aiOn) && matches(entry, words),
    );
    const found: Entry[] = (items.data ?? []).map((item) => ({
      id: `item-${item.id}`,
      label: item.display_name,
      group: "Your items",
      href: `/wardrobe/${item.id}`,
    }));
    return [...fixed, ...found];
  }, [words, items.data, status.data]);

  function go(entry: Entry | undefined) {
    if (!entry) return;
    setOpen(false);
    setQuery("");
    router.push(entry.href);
  }

  const current = Math.min(active, Math.max(results.length - 1, 0));
  const optionId = (index: number) => `${listId}-${index}`;

  return (
    <>
      <Button
        variant="quiet"
        className="ml-auto text-ink-soft lg:mr-2"
        onClick={() => setOpen(true)}
        aria-keyshortcuts={mac ? "Meta+K" : "Control+K"}
      >
        <Search aria-hidden />
        <span className="sr-only sm:not-sr-only">Jump to</span>
        <kbd className="hidden rounded border border-line px-1.5 text-xs text-ink-soft sm:inline">
          {mac ? "⌘K" : "Ctrl K"}
        </kbd>
      </Button>
      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) setQuery("");
        }}
      >
        <DialogContent className="top-[15%] max-w-lg translate-y-0 gap-3">
          <DialogHeader>
            <DialogTitle>Jump to</DialogTitle>
            <DialogDescription className="sr-only">
              Type to find a page, an action, or one of your items. Use the
              arrow keys and Enter.
            </DialogDescription>
          </DialogHeader>
          <Input
            role="combobox"
            aria-label="Find a page, action, or item"
            aria-expanded={results.length > 0}
            aria-controls={listId}
            aria-activedescendant={
              results.length ? optionId(current) : undefined
            }
            autoComplete="off"
            placeholder="Find a page, an action, or an item"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActive(0);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setActive((current + 1) % Math.max(results.length, 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActive(
                  (current - 1 + results.length) % Math.max(results.length, 1),
                );
              } else if (event.key === "Enter") {
                event.preventDefault();
                go(results[current]);
              }
            }}
          />
          <ul
            id={listId}
            role="listbox"
            aria-label="Results"
            className="max-h-80 overflow-y-auto"
          >
            {results.length === 0 ? (
              <li className="px-3 py-2 text-sm text-ink-soft">
                Nothing matches.
              </li>
            ) : (
              results.map((entry, index) => (
                <li
                  key={entry.id}
                  id={optionId(index)}
                  role="option"
                  aria-selected={index === current}
                  onMouseMove={() => setActive(index)}
                  onClick={() => go(entry)}
                  className={cn(
                    "flex min-h-11 cursor-pointer items-center justify-between gap-3 rounded-lg px-3",
                    index === current && "bg-tile",
                  )}
                >
                  <span className="min-w-0 truncate">{entry.label}</span>
                  <span className="flex shrink-0 items-center gap-2 text-xs text-ink-soft">
                    {entry.group}
                    {index === current && (
                      <CornerDownLeft aria-hidden className="size-4" />
                    )}
                  </span>
                </li>
              ))
            )}
          </ul>
        </DialogContent>
      </Dialog>
    </>
  );
}
