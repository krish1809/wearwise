import Link from "next/link";

import {
  GarmentShirt,
  GarmentSneaker,
  GarmentTrousers,
} from "@/components/garment-drawings";
import { DemoButton } from "@/components/demo-button";
import { Button } from "@/components/ui/button";
import { focusRing } from "@/lib/utils";

import { WarmUp } from "./warm-up";

const FEATURES = [
  {
    title: "Your wardrobe, photo first",
    text: "Everything you wear, from shirts to shoes, watches, and fragrance, in one place you can search.",
  },
  {
    title: "Outfits with reasons",
    text: "Combinations from what you already own, each with a plain sentence on why it works.",
  },
  {
    title: "Buy what adds the most",
    text: "Before you buy something, see how many new outfits it would make and what you own that's already close.",
  },
] as const;

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-4 py-5 sm:px-8">
        <span className="font-display text-xl font-semibold tracking-tight">
          WearWise
        </span>
        <Button asChild variant="quiet">
          <Link href="/login">Log in</Link>
        </Button>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-24 sm:px-8">
        <section className="grid items-center gap-10 py-8 lg:grid-cols-2 lg:gap-16 lg:py-16">
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight">
              Know what to wear.
            </h1>
            <p className="mt-4 max-w-prose text-lg text-ink-soft">
              WearWise is a wardrobe app for the clothes you already own. It
              shows you the outfits you can make, says why they work, and tells
              you what a new purchase would add before you spend.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild>
                <Link href="/register">Create an account</Link>
              </Button>
              <DemoButton />
            </div>
            <p className="mt-3 text-sm text-ink-soft">
              The demo is a sample wardrobe of everyday staples, yours for a
              day. No sign-up.
            </p>
          </div>
          <FlatLay />
        </section>

        <section
          aria-labelledby="what-it-does"
          className="border-t border-line pt-12"
        >
          <h2 id="what-it-does" className="sr-only">
            What WearWise does
          </h2>
          <ul className="grid gap-8 sm:grid-cols-3">
            {FEATURES.map((feature) => (
              <li key={feature.title}>
                <h3 className="text-lg font-medium">{feature.title}</h3>
                <p className="mt-2 text-ink-soft">{feature.text}</p>
              </li>
            ))}
          </ul>
        </section>
      </main>
      <footer className="mx-auto max-w-5xl px-4 pb-10 text-sm text-ink-soft sm:px-8">
        <Link
          href="/privacy"
          className={`rounded underline underline-offset-2 ${focusRing}`}
        >
          Privacy
        </Link>
      </footer>
      <WarmUp />
    </div>
  );
}

/** Garments laid out on the studio tile, the way the app shows an outfit. Decoration only. */
function FlatLay() {
  return (
    <div
      aria-hidden
      className="grid aspect-4/3 grid-cols-2 grid-rows-2 gap-4 rounded-xl bg-tile p-6 sm:p-10"
    >
      <div className="flex items-center justify-center">
        <GarmentShirt />
      </div>
      <div className="row-span-2 flex items-center justify-center">
        <GarmentTrousers />
      </div>
      <div className="flex items-center justify-center">
        <GarmentSneaker />
      </div>
    </div>
  );
}
