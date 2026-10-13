import Link from "next/link";

import { focusRing } from "@/lib/utils";

// Log in and register: the wordmark, then one narrow form in the middle of the page.
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="px-4 py-6 sm:px-8">
        <Link
          href="/"
          className={`rounded-lg font-display text-xl font-semibold tracking-tight ${focusRing}`}
        >
          WearWise
        </Link>
      </header>
      <main className="flex flex-1 justify-center px-4 pt-6 pb-16 sm:pt-16">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  );
}
