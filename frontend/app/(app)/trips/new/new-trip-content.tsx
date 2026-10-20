"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import {
  type ChosenPlace,
  PlaceSearch,
} from "@/components/weather/place-search";
import { type ApiProblem, problemFrom } from "@/lib/api/errors";
import { dayLabel, isoDay, todayIso } from "@/lib/dates";
import type { Reference } from "@/lib/profile";
import { useCreateTrip } from "@/lib/trips";

const MAX_DAYS = 14;

export function NewTripContent() {
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <BackLink href="/trips">Trips</BackLink>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Plan a trip
      </h1>
      <WardrobeData>
        {({ reference }) => <TripForm reference={reference} />}
      </WardrobeData>
    </div>
  );
}

function daysBetween(start: string, end: string): string[] {
  if (!start || !end || end < start) return [];
  const days = [];
  const cursor = new Date(`${start}T00:00:00`);
  const last = new Date(`${end}T00:00:00`);
  while (cursor <= last && days.length <= MAX_DAYS) {
    days.push(isoDay(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

function TripForm({ reference }: { reference: Reference }) {
  const router = useRouter();
  const create = useCreateTrip();
  const [place, setPlace] = useState<ChosenPlace | null>(null);
  const [start, setStart] = useState(todayIso());
  const [end, setEnd] = useState(todayIso());
  const [occasion, setOccasion] = useState("");
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const days = daysBetween(start, end);

  async function submit() {
    const fields: Record<string, string> = {};
    if (!place) fields.destination = "Find the place you're going to.";
    if (!occasion) fields.occasion_id = "Choose what the days are mostly for.";
    if (end < start) fields.end_date = "The trip ends before it starts.";
    else if (days.length > MAX_DAYS)
      fields.end_date = `Plan up to ${MAX_DAYS} days at a time.`;
    if (Object.keys(fields).length > 0) {
      setProblem({
        code: "invalid_input",
        message: "Check the highlighted fields.",
        fields,
      });
      return;
    }
    setProblem(null);
    try {
      const trip = await create.mutateAsync({
        destination: place?.label ?? "",
        latitude: place?.latitude ?? null,
        longitude: place?.longitude ?? null,
        start_date: start,
        end_date: end,
        occasion_id: occasion,
        day_occasions: Object.fromEntries(
          Object.entries(overrides).filter(
            ([day, value]) => value && days.includes(day),
          ),
        ),
      });
      toast.success("Packing list ready");
      router.push(`/trips/${trip.id}`);
    } catch (error) {
      setProblem(problemFrom(error));
    }
  }

  return (
    <form
      noValidate
      className="flex flex-col gap-6"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {problem && <Alert tone="error">{problem.message}</Alert>}
      <PlaceSearch
        label="Where to"
        hint="For the forecast there. Without one, the trip goes by your weather setting."
        value={place}
        onChange={setPlace}
        error={problem?.fields.destination}
      />
      <div className="grid gap-4 sm:max-w-md sm:grid-cols-2">
        <Field label="From" error={problem?.fields.start_date}>
          {(control) => (
            <Input
              type="date"
              value={start}
              min={todayIso()}
              onChange={(event) => setStart(event.target.value)}
              {...control}
            />
          )}
        </Field>
        <Field label="Until" error={problem?.fields.end_date}>
          {(control) => (
            <Input
              type="date"
              value={end}
              min={start}
              onChange={(event) => setEnd(event.target.value)}
              {...control}
            />
          )}
        </Field>
      </div>
      <Field
        label="What the days are mostly for"
        error={problem?.fields.occasion_id}
      >
        {(control) => (
          <Select
            value={occasion}
            onChange={(event) => setOccasion(event.target.value)}
            className="sm:max-w-sm"
            {...control}
          >
            <option value="">Choose an occasion</option>
            {reference.occasions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </Select>
        )}
      </Field>
      {days.length > 1 && days.length <= MAX_DAYS && (
        <details className="flex flex-col gap-3 rounded-lg bg-surface p-4">
          <summary className="cursor-pointer font-medium">
            A day that&apos;s different (a wedding, a meeting)
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {days.map((day) => (
              <Field key={day} label={dayLabel(day)}>
                {(control) => (
                  <Select
                    value={overrides[day] ?? ""}
                    onChange={(event) =>
                      setOverrides({ ...overrides, [day]: event.target.value })
                    }
                    {...control}
                  >
                    <option value="">Same as the rest</option>
                    {reference.occasions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            ))}
          </div>
        </details>
      )}
      <div>
        <Button type="submit" loading={create.isPending}>
          Make the packing list
        </Button>
      </div>
    </form>
  );
}
