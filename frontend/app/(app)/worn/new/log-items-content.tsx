"use client";

import { CheckIcon, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { type ApiProblem, problemFrom } from "@/lib/api/errors";
import { dayPhrase, todayIso } from "@/lib/dates";
import { useLogWear } from "@/lib/outfits";
import type { Reference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";
import { type ItemSummary, useItems } from "@/lib/wardrobe";

/** Log loose items: what was worn that isn't a saved outfit. */
export function LogItemsContent() {
  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/worn">Wear log</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Log what you wore
        </h1>
        <p className="mt-1 text-ink-soft">
          Choose the pieces. For a saved outfit, use &ldquo;I wore this
          today&rdquo; on its page instead.
        </p>
      </div>
      <WardrobeData>
        {({ reference }) => <LogForm reference={reference} />}
      </WardrobeData>
    </div>
  );
}

function LogForm({ reference }: { reference: Reference }) {
  const router = useRouter();
  const log = useLogWear();
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState<Map<string, ItemSummary>>(new Map());
  const [day, setDay] = useState(todayIso());
  const [occasion, setOccasion] = useState("");
  const [note, setNote] = useState("");
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const [missing, setMissing] = useState<string | null>(null);
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const items = useItems({
    q,
    group: [],
    color: [],
    season: [],
    occasion: [],
    style: [],
    status: [],
    archived: false,
    sort: "category",
  });
  const shown = (items.data?.pages ?? []).flatMap((page) => page.items);

  function toggle(item: ItemSummary) {
    const next = new Map(picked);
    if (next.has(item.id)) next.delete(item.id);
    else next.set(item.id, item);
    setPicked(next);
    setMissing(null);
  }

  async function submit() {
    setProblem(null);
    if (picked.size === 0) {
      setMissing("Choose at least one item you wore.");
      return;
    }
    try {
      await log.mutateAsync({
        worn_on: day,
        item_ids: [...picked.keys()],
        occasion_id: occasion || null,
        note: note.trim() || null,
      });
      toast.success(
        `Logged ${picked.size} ${picked.size === 1 ? "piece" : "pieces"} ${dayPhrase(day)}`,
      );
      router.push("/worn");
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
      <section aria-labelledby="pick-heading" className="flex flex-col gap-3">
        <h2 id="pick-heading" className="text-lg font-medium">
          What you wore
          <span className="ml-2 text-base font-normal text-ink-soft tabular-nums">
            {picked.size} chosen
          </span>
        </h2>
        {missing && (
          <p role="alert" className="text-sm text-skip">
            {missing}
          </p>
        )}
        <div className="relative sm:max-w-sm">
          <Search
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-ink-soft"
          />
          <Input
            type="search"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            aria-label="Search your wardrobe"
            placeholder="Search your wardrobe"
            className="pl-10"
          />
        </div>
        <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {shown.map((item) => {
            const on = picked.has(item.id);
            return (
              <li key={item.id}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggle(item)}
                  className={cn("group w-full rounded-lg text-left", focusRing)}
                >
                  <span
                    className={cn(
                      "relative flex aspect-3/4 items-center justify-center rounded-lg bg-tile p-2 *:max-h-full *:max-w-full",
                      on &&
                        "ring-2 ring-indigo ring-offset-2 ring-offset-paper",
                    )}
                  >
                    <ItemPhoto
                      photo={item.photo}
                      alt=""
                      hex={item.color_hex ?? familyHex.get(item.color_primary)}
                    />
                    {on && (
                      <span className="absolute top-1.5 right-1.5 grid size-6 place-content-center rounded-full bg-indigo text-white">
                        <CheckIcon aria-hidden className="size-4" />
                      </span>
                    )}
                  </span>
                  <span className="mt-1 block truncate text-sm">
                    {item.display_name}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        {items.hasNextPage && (
          <Button
            type="button"
            variant="quiet"
            className="self-start"
            loading={items.isFetchingNextPage}
            onClick={() => void items.fetchNextPage()}
          >
            Show more
          </Button>
        )}
      </section>

      <div className="grid gap-5 sm:max-w-xl sm:grid-cols-2">
        <Field label="Day" error={problem?.fields.worn_on}>
          {(control) => (
            <Input
              type="date"
              value={day}
              max={todayIso()}
              onChange={(event) => setDay(event.target.value)}
              {...control}
            />
          )}
        </Field>
        <Field label="Occasion (optional)" error={problem?.fields.occasion_id}>
          {(control) => (
            <Select
              value={occasion}
              onChange={(event) => setOccasion(event.target.value)}
              {...control}
            >
              <option value="">None</option>
              {reference.occasions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      <Field
        label="Note (optional)"
        error={problem?.fields.note}
        className="sm:max-w-xl"
      >
        {(control) => (
          <Textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            maxLength={500}
            {...control}
          />
        )}
      </Field>
      <div>
        <Button type="submit" loading={log.isPending}>
          Log what I wore
        </Button>
      </div>
    </form>
  );
}
