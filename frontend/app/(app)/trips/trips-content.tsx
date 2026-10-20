"use client";

import { Luggage, Plus } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { BackLink } from "@/components/wardrobe/wardrobe-data";
import { dayLabel } from "@/lib/dates";
import { useTrips } from "@/lib/trips";
import { cn, focusRing } from "@/lib/utils";

export function TripsContent() {
  const trips = useTrips();

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <BackLink href="/week">My Week</BackLink>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Trips
        </h1>
        <Button asChild>
          <Link href="/trips/new">
            <Plus aria-hidden />
            Plan a trip
          </Link>
        </Button>
      </div>
      {trips.isError ? (
        <ErrorState
          title="Couldn't load your trips"
          action={
            <Button variant="secondary" onClick={() => void trips.refetch()}>
              Try again
            </Button>
          }
        >
          Check your connection and try again.
        </ErrorState>
      ) : !trips.data ? (
        <div aria-busy="true" className="flex flex-col gap-2">
          {[0, 1].map((key) => (
            <Skeleton key={key} className="h-16" />
          ))}
          <span role="status" className="sr-only">
            Loading
          </span>
        </div>
      ) : trips.data.length === 0 ? (
        <EmptyState
          icon={<Luggage />}
          title="No trips yet"
          action={
            <Button asChild>
              <Link href="/trips/new">Plan a trip</Link>
            </Button>
          }
        >
          Give the dates and what each day is for, and WearWise makes a compact
          packing list with an outfit for every day.
        </EmptyState>
      ) : (
        <ul className="flex flex-col gap-2">
          {trips.data.map((trip) => (
            <li key={trip.id}>
              <Link
                href={`/trips/${trip.id}`}
                className={cn(
                  "flex items-center justify-between gap-3 rounded-lg bg-surface px-4 py-3 hover:bg-tile",
                  focusRing,
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">
                    {trip.destination}
                  </span>
                  <span className="block text-sm text-ink-soft">
                    {dayLabel(trip.start_date)} to {dayLabel(trip.end_date)}
                  </span>
                </span>
                <span className="shrink-0 text-sm text-ink-soft">
                  {trip.item_count} {trip.item_count === 1 ? "item" : "items"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
