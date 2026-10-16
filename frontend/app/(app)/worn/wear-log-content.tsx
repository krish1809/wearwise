"use client";

import { CalendarCheck, Plus } from "lucide-react";
import Link from "next/link";

import { WearLogList } from "@/components/outfits/wear-log-list";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { WardrobeData } from "@/components/wardrobe/wardrobe-data";

export function WearLogContent() {
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            Wear log
          </h1>
          <p className="mt-1 text-ink-soft">
            What you wore, day by day. Every wear count comes from here.
          </p>
        </div>
        <Button asChild>
          <Link href="/worn/new">
            <Plus aria-hidden />
            Log what you wore
          </Link>
        </Button>
      </div>
      <WardrobeData>
        {({ reference }) => (
          <WearLogList
            filters={{}}
            reference={reference}
            empty={
              <EmptyState
                icon={<CalendarCheck />}
                title="Nothing logged yet"
                action={
                  <Button asChild variant="secondary">
                    <Link href="/outfits">Choose an outfit</Link>
                  </Button>
                }
              >
                Mark an outfit as worn from its page, or log loose items.
              </EmptyState>
            }
          />
        )}
      </WardrobeData>
    </div>
  );
}
