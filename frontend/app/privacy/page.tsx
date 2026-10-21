import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { focusRing } from "@/lib/utils";

export const metadata: Metadata = { title: "Privacy · WearWise" };

const REPOSITORY = "https://github.com/krish1809/wearwise";

const SERVICES = [
  {
    name: "Vercel",
    what: "Hosts this website. Like any host, it sees your IP address and the pages you open.",
  },
  {
    name: "Render",
    what: "Runs the WearWise server. Its logs record each request (the page asked for and your IP address) and are kept for a short time.",
  },
  {
    name: "Neon",
    what: "Stores the database that holds your account and wardrobe.",
  },
  {
    name: "Backblaze",
    what: "Stores your photos in a private bucket. Only the WearWise server reads them, and it shows each photo only to the account it belongs to.",
  },
  {
    name: "Open-Meteo",
    what: "Gives the forecast and the place search. It receives your city's position, rounded to about a kilometre, and the place names you search for. The requests come from the WearWise server, not your browser.",
  },
  {
    name: "Anthropic",
    what: "Only if the stylist is switched on in this copy of WearWise, and only when you use it: your messages, the wardrobe details the stylist looks up to answer them, and a photo when you press \"Fill in from the photo\". If you turn on the weekly email, the details of the pieces it picks and your style choices, to word it: never your email address, measurements, or photos. Anthropic's commercial terms say this data isn't used to train its models.",
  },
  {
    name: "Resend",
    what: "Sends WearWise's emails: it gets your address and the email itself. That's only the weekly email if you turn it on, the link to confirm your address, and a link to set a new password if you ask for one.",
  },
  {
    name: "Tavily",
    what: "Searches the web for what's in fashion in India, for the Trend Scout. It gets only search words about fashion and the season, never anything about you.",
  },
  {
    name: "GitHub",
    what: "Runs WearWise's scheduled jobs, the Trend Scout and the weekly email, on its machines. The weekly email's job reads what it needs from the database to make each person's picks.",
  },
  {
    name: "Shops",
    what: "When you paste a product link, the WearWise server reads that one page, if the shop allows it; the shop sees the server, not you. Shop pictures load straight from the shop, without saying which page you were on. Links to shop searches open the shop's own site.",
  },
] as const;

export default function PrivacyPage() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-4 py-5 sm:px-8">
        <Link
          href="/"
          className={`rounded-lg font-display text-xl font-semibold tracking-tight ${focusRing}`}
        >
          WearWise
        </Link>
        <Button asChild variant="quiet">
          <Link href="/login">Log in</Link>
        </Button>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-24 sm:px-8">
        <h1 className="mt-6 font-display text-2xl font-semibold tracking-tight">
          Privacy
        </h1>
        <p className="mt-3 max-w-prose text-lg text-ink-soft">
          What WearWise stores, who else sees any of it, and how to take it with
          you or delete it. No ads, no analytics, and nothing is sold.
        </p>

        <Section title="What's stored">
          <ul className="list-disc space-y-2 pl-5">
            <li>
              Your account: email address, name if you gave one, and your
              password as a one-way hash (Argon2id), never the password itself.
            </li>
            <li>
              Everything you add: your profile answers, items and their photos,
              outfits, the wear log, plans, events, trips, the shopping list,
              brand notes, and conversations with the stylist.
            </li>
            <li>
              Photos are cleaned when they arrive: location and every other
              hidden detail are removed. A photo uploaded but never saved with
              an item is deleted after about a day.
            </li>
            <li>
              The outfits suggested to you, and whether you liked them, so the
              suggestions can get better.
            </li>
            <li>
              Your weekly picks, and whether you said &ldquo;not for me&rdquo;
              to one. If you turn on the weekly email: when you confirmed your
              address and asked for it, and a record of each email sent, kept 90
              days, without the address.
            </li>
            <li>
              Trends found on the web, with the pages they came from: nothing
              about you.
            </li>
            <li>
              To stop repeated log-in attempts, a count of recent attempts by IP
              address and by a scrambled form of the email address. These counts
              are deleted within a day.
            </li>
            <li>
              When something breaks, a short report of what went wrong and on
              which page, without your account or anything you typed. Reports
              are deleted after 30 days.
            </li>
          </ul>
        </Section>

        <Section title="In your browser">
          <p>
            One cookie keeps you logged in. It can&apos;t be read by scripts and
            is sent only to WearWise. The light or dark theme you choose is kept
            in your browser&apos;s storage. There are no tracking or advertising
            cookies.
          </p>
        </Section>

        <Section title="Who else sees what">
          <dl className="flex flex-col gap-4">
            {SERVICES.map((service) => (
              <div key={service.name}>
                <dt className="font-medium">{service.name}</dt>
                <dd className="mt-1 text-ink-soft">{service.what}</dd>
              </div>
            ))}
          </dl>
        </Section>

        <Section title="Taking it with you, or deleting it">
          <p>
            In Settings, under Account, &quot;Download my data&quot; gives you a
            zip file with everything stored for your account, including every
            photo. &quot;Delete account&quot; removes your account, every row of
            your data, and every photo straight away. The database host keeps a
            short history for restoring from mistakes; after that window,
            nothing is left. A demo started with &quot;Try the demo&quot; is
            deleted, with anything added to it, a day after it starts.
          </p>
        </Section>

        <Section title="Questions">
          <p>
            WearWise is a personal project, and its code is public. Ask on{" "}
            <a
              href={REPOSITORY}
              className={`underline underline-offset-2 ${focusRing}`}
            >
              its GitHub page
            </a>
            .
          </p>
        </Section>
      </main>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-10 max-w-prose">
      <h2 className="text-lg font-medium">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}
