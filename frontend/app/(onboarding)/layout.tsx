import Link from "next/link";

import { focusRing } from "@/lib/utils";

// Onboarding: no navigation to wander off into, one step at a time. proxy.ts sends anyone
// without a session cookie to log in first.
export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="px-4 py-6 sm:px-8">
        <Link
          href="/home"
          className={`rounded-lg font-display text-xl font-semibold tracking-tight ${focusRing}`}
        >
          WearWise
        </Link>
      </header>
      <main
        id="main"
        className="flex flex-1 justify-center px-4 pt-2 pb-16 sm:pt-8"
      >
        <div className="w-full max-w-2xl">{children}</div>
      </main>
    </div>
  );
}
