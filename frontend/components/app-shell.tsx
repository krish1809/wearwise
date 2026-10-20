"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  CalendarDays,
  ChartColumn,
  Ellipsis,
  House,
  Layers,
  Shirt,
  ShoppingBag,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AvatarMenu } from "@/components/ui/avatar-menu";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
  BottomSheetTrigger,
} from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api/client";
import { type User, useCurrentUser } from "@/lib/auth";
import { useSlow } from "@/lib/hooks";
import { cn, focusRing } from "@/lib/utils";

// Only pages that exist appear in the navigation; new ones join as they are built.
const NAV = [
  { href: "/home", label: "Home", icon: House },
  { href: "/wardrobe", label: "Wardrobe", icon: Shirt },
  { href: "/outfits", label: "Outfits", icon: Layers },
  { href: "/week", label: "My Week", icon: CalendarDays },
  { href: "/shopping", label: "Shopping", icon: ShoppingBag },
  { href: "/insights", label: "Insights", icon: ChartColumn },
  { href: "/guide", label: "Style Guide", icon: BookOpen },
] as const;

// The phone's tab bar has room for four; the rest are under More.
const TABS = NAV.slice(0, 4);
const MORE = NAV.slice(4);

function isActive(pathname: string | null, href: string): boolean {
  if (pathname === null) return false;
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * The frame around every logged-in page: sidebar on desktop, tab bar on phones. The frame
 * draws straight away; each page shows its own placeholder until the API says who is here.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { data: user, isError, refetch } = useCurrentUser();

  // The address is only known per request on pages like /wardrobe/[id], so the parts that read
  // it wait in Suspense; meanwhile the navigation draws without the current page marked.
  return (
    <div className="min-h-screen lg:flex">
      {/* The first Tab stop: lets keyboard users jump past the navigation. */}
      <a
        href="#main"
        className={cn(
          "sr-only rounded-lg bg-surface px-4 py-3 font-medium focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50",
          focusRing,
        )}
      >
        Skip to content
      </a>
      <Suspense fallback={<Sidebar pathname={null} />}>
        <WithPathname>
          {(pathname) => <Sidebar pathname={pathname} />}
        </WithPathname>
      </Suspense>
      <Suspense>
        <SessionWatch ended={user === null} />
      </Suspense>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar user={user ?? undefined} />
        <main
          id="main"
          tabIndex={-1}
          className="flex-1 px-4 pt-6 pb-28 outline-none sm:px-6 lg:px-10 lg:pt-8 lg:pb-12"
        >
          {isError ? (
            <ErrorState
              className="mx-auto max-w-md"
              title="Couldn't reach WearWise"
              action={
                <Button variant="secondary" onClick={() => void refetch()}>
                  Try again
                </Button>
              }
            >
              Check your connection and try again.
            </ErrorState>
          ) : (
            children
          )}
          <Credits />
        </main>
      </div>
      <Suspense fallback={<TabBar pathname={null} />}>
        <WithPathname>
          {(pathname) => <TabBar pathname={pathname} />}
        </WithPathname>
      </Suspense>
    </div>
  );
}

/** The weather and place data come with a licence that asks for credit. */
function Credits() {
  return (
    <footer className="mt-16 text-xs text-ink-soft">
      Weather data by{" "}
      <a
        href="https://open-meteo.com/"
        className={cn("underline underline-offset-2", focusRing)}
      >
        Open-Meteo.com
      </a>{" "}
      (
      <a
        href="https://creativecommons.org/licenses/by/4.0/"
        className={cn("underline underline-offset-2", focusRing)}
      >
        CC BY 4.0
      </a>
      ). Place search based on{" "}
      <a
        href="https://www.geonames.org/"
        className={cn("underline underline-offset-2", focusRing)}
      >
        GeoNames
      </a>
      .
    </footer>
  );
}

function WithPathname({
  children,
}: {
  children: (pathname: string) => React.ReactNode;
}) {
  return children(usePathname());
}

/** The browser had a cookie, but the session had ended (the API removed the cookie). */
function SessionWatch({ ended }: { ended: boolean }) {
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (ended) {
      router.replace(
        `/login?reason=expired&next=${encodeURIComponent(pathname)}`,
      );
    }
  }, [ended, router, pathname]);
  return null;
}

/** What a logged-in page shows until the API has said who is logged in. */
export function PageLoading() {
  const waking = useSlow(true);
  return (
    <div aria-busy="true" className="flex max-w-md flex-col gap-3">
      <Skeleton className="h-10 w-1/2" />
      <Skeleton className="h-4 w-3/4" />
      <p role="status" className="mt-4 text-sm text-ink-soft">
        {waking ? (
          "Waking the server. This can take up to a minute."
        ) : (
          <span className="sr-only">Loading</span>
        )}
      </p>
    </div>
  );
}

function Wordmark({ className }: { className?: string }) {
  return (
    <Link
      href="/home"
      className={cn(
        "rounded-lg font-display text-xl font-semibold tracking-tight",
        focusRing,
        className,
      )}
    >
      WearWise
    </Link>
  );
}

function Sidebar({ pathname }: { pathname: string | null }) {
  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line px-4 py-5 lg:flex">
      <Wordmark className="self-start px-3 py-1" />
      <nav aria-label="Main" className="mt-8">
        <ul className="flex flex-col gap-1">
          {NAV.map(({ href, label, icon: Icon }) => (
            <li key={href}>
              <Link
                href={href}
                aria-current={isActive(pathname, href) ? "page" : undefined}
                className={cn(
                  "flex min-h-11 items-center gap-3 rounded-lg px-3 font-medium text-ink-soft transition-colors",
                  "hover:bg-tile hover:text-ink aria-[current=page]:bg-indigo/10 aria-[current=page]:text-indigo",
                  focusRing,
                )}
              >
                <Icon aria-hidden className="size-5" />
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}

function TopBar({ user }: { user: User | undefined }) {
  const queryClient = useQueryClient();
  const router = useRouter();

  async function logOut() {
    try {
      await api.POST("/api/v1/auth/logout");
    } catch {
      toast.error("Couldn't log out. Check your connection and try again.");
      return;
    }
    queryClient.clear();
    router.replace("/");
    toast("You're logged out.");
  }

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-line bg-paper px-4 sm:px-6 lg:justify-end lg:px-10">
      <Wordmark className="lg:hidden" />
      {user?.is_demo && (
        <span className="mr-3 ml-auto rounded-full bg-consider/15 px-3 py-1 text-sm font-medium text-ink">
          Demo account
        </span>
      )}
      {user ? (
        <AvatarMenu
          name={user.name}
          email={user.email}
          settingsHref="/settings"
          onLogOut={() => void logOut()}
        />
      ) : (
        <Skeleton className="size-11 rounded-full" />
      )}
    </header>
  );
}

function TabBar({ pathname }: { pathname: string | null }) {
  const [open, setOpen] = useState(false);
  const inMore = MORE.some(({ href }) => isActive(pathname, href));
  const tab = cn(
    "flex min-h-16 w-full flex-col items-center justify-center gap-1 text-xs font-medium text-ink-soft",
    "hover:text-ink aria-[current=page]:text-indigo",
    focusRing,
  );
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <ul
        className="grid"
        style={{
          gridTemplateColumns: `repeat(${TABS.length + 1}, minmax(0, 1fr))`,
        }}
      >
        {TABS.map(({ href, label, icon: Icon }) => (
          <li key={href}>
            <Link
              href={href}
              aria-current={isActive(pathname, href) ? "page" : undefined}
              className={tab}
            >
              <Icon aria-hidden className="size-6" />
              {label}
            </Link>
          </li>
        ))}
        <li>
          <BottomSheet open={open} onOpenChange={setOpen}>
            <BottomSheetTrigger
              aria-current={inMore ? "page" : undefined}
              className={tab}
            >
              <Ellipsis aria-hidden className="size-6" />
              More
            </BottomSheetTrigger>
            <BottomSheetContent>
              <BottomSheetHeader>
                <BottomSheetTitle>More</BottomSheetTitle>
              </BottomSheetHeader>
              <ul className="flex flex-col gap-1 p-4">
                {MORE.map(({ href, label, icon: Icon }) => (
                  <li key={href}>
                    <Link
                      href={href}
                      onClick={() => setOpen(false)}
                      aria-current={
                        isActive(pathname, href) ? "page" : undefined
                      }
                      className={cn(
                        "flex min-h-12 items-center gap-3 rounded-lg px-3 font-medium text-ink",
                        "hover:bg-tile aria-[current=page]:bg-indigo/10 aria-[current=page]:text-indigo",
                        focusRing,
                      )}
                    >
                      <Icon aria-hidden className="size-5" />
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </BottomSheetContent>
          </BottomSheet>
        </li>
      </ul>
    </nav>
  );
}
