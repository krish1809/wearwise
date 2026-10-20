"use client";

import { Shirt } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { SuggestionCard } from "@/components/outfits/suggestion-card";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import type { Profile, Reference } from "@/lib/profile";
import {
  type Suggestion,
  type Suggestions,
  useSuggest,
} from "@/lib/suggestions";
import { useItem } from "@/lib/wardrobe";

const COUNT = 6;

export function SuggestContent() {
  const anchorId = useSearchParams().get("with");

  return (
    <div className="flex flex-col gap-6">
      {anchorId ? (
        <BackLink href={`/wardrobe/${anchorId}`}>Item</BackLink>
      ) : (
        <BackLink href="/outfits">Outfits</BackLink>
      )}
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        {anchorId ? "What goes with this?" : "Suggest outfits"}
      </h1>
      <WardrobeData>
        {({ reference, profile }) => (
          <Suggester
            key={anchorId ?? "all"}
            reference={reference}
            profile={profile}
            anchorId={anchorId}
          />
        )}
      </WardrobeData>
    </div>
  );
}

/** The first occasion the person said they dress for, if any. */
function firstOccasion(reference: Reference, profile: Profile): string {
  const known = new Set(reference.occasions.map((o) => o.id));
  return profile.occasion_ids.find((id) => known.has(id)) ?? "";
}

function Suggester({
  reference,
  profile,
  anchorId,
}: {
  reference: Reference;
  profile: Profile;
  anchorId: string | null;
}) {
  // Built around a piece, the occasion is optional: the piece sets the level of dress.
  const [occasion, setOccasion] = useState(
    anchorId ? "" : firstOccasion(reference, profile),
  );
  const [season, setSeason] = useState("");
  const [style, setStyle] = useState("");
  const [results, setResults] = useState<Suggestions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const suggest = useSuggest();
  const started = useRef(false);

  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const occasions = new Map(reference.occasions.map((o) => [o.id, o.name]));
  const seasonNames = new Map(reference.seasons.map((s) => [s.id, s.name]));

  async function run() {
    setError(null);
    try {
      setResults(
        await suggest.mutateAsync({
          occasion_id: occasion || null,
          season: season || null,
          style_id: style || null,
          anchor_item_ids: anchorId ? [anchorId] : [],
          count: COUNT,
        }),
      );
    } catch (failure) {
      setError(problemFrom(failure).message);
    }
  }

  // Suggest straight away when the occasion is known (or a piece sets the level); once only,
  // even in development, where effects run twice.
  const ready = Boolean(occasion || anchorId);
  useEffect(() => {
    if (started.current || !ready) return;
    started.current = true;
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function replace(next: Suggestion) {
    setResults((current) =>
      current
        ? {
            ...current,
            suggestions: current.suggestions.map((s) =>
              s.id === next.id ? next : s,
            ),
          }
        : current,
    );
  }

  const shown = results?.suggestions ?? [];

  return (
    <div className="flex flex-col gap-8">
      {anchorId && <AnchorPiece id={anchorId} familyHex={familyHex} />}
      <form
        noValidate
        className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end"
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
      >
        <Field label={anchorId ? "Occasion (optional)" : "Occasion"}>
          {(control) => (
            <Select
              value={occasion}
              onChange={(event) => setOccasion(event.target.value)}
              className="sm:w-60"
              {...control}
            >
              {anchorId ? (
                <option value="">Any occasion</option>
              ) : (
                !occasion && <option value="">Choose an occasion</option>
              )}
              {reference.occasions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Season">
          {(control) => (
            <Select
              value={season}
              onChange={(event) => setSeason(event.target.value)}
              className="sm:w-48"
              {...control}
            >
              <option value="">This season</option>
              {reference.seasons.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Style">
          {(control) => (
            <Select
              value={style}
              onChange={(event) => setStyle(event.target.value)}
              className="sm:w-56"
              {...control}
            >
              <option value="">
                {profile.style_profile_ids.length > 0
                  ? "Your styles"
                  : "Any style"}
              </option>
              {reference.style_profiles.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Button
          type="submit"
          loading={suggest.isPending}
          disabled={!occasion && !anchorId}
        >
          {results ? "Suggest again" : "Suggest outfits"}
        </Button>
      </form>

      {error ? (
        <ErrorState
          title="Couldn't suggest outfits"
          action={
            <Button variant="secondary" onClick={() => void run()}>
              Try again
            </Button>
          }
        >
          {error}
        </ErrorState>
      ) : !results && !suggest.isPending ? (
        <p className="text-ink-soft">
          Choose an occasion, and WearWise suggests outfits from what you have.
        </p>
      ) : !results || suggest.isPending ? (
        <div aria-busy="true" className="grid gap-x-6 gap-y-10 sm:grid-cols-2">
          {[0, 1].map((key) => (
            <Skeleton key={key} className="aspect-[5/4]" />
          ))}
          <span role="status" className="sr-only">
            Finding outfits
          </span>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {shown.length === 0 ? (
            // Announce why, since the heading below only says that nothing fits.
            <p role="status" className="sr-only">
              {results.missing.map((missing) => missing.text).join(" ")}
            </p>
          ) : (
            <p role="status" className="text-ink-soft">
              {`${shown.length} ${shown.length === 1 ? "outfit" : "outfits"}. Season: ${
                seasonNames.get(results.season) ?? results.season
              }.`}
            </p>
          )}
          {results.note && <Alert>{results.note}</Alert>}
          {shown.length === 0 ? (
            <EmptyState
              icon={<Shirt />}
              title="No outfit fits yet"
              action={
                <Button asChild>
                  <Link href="/wardrobe/new">Add an item</Link>
                </Button>
              }
            >
              <ul className="flex flex-col gap-1">
                {results.missing.map((missing) => (
                  <li key={`${missing.slot}-${missing.code}`}>
                    {missing.text}
                  </li>
                ))}
              </ul>
            </EmptyState>
          ) : (
            <>
              {results.compromise && results.missing.length > 0 && (
                <ul className="flex flex-col gap-1 text-sm text-ink-soft">
                  {results.missing.map((missing) => (
                    <li key={`${missing.slot}-${missing.code}`}>
                      {missing.text}
                    </li>
                  ))}
                </ul>
              )}
              <ul className="grid gap-x-6 gap-y-12 sm:grid-cols-2 xl:grid-cols-3">
                {shown.map((suggestion) => (
                  <li key={suggestion.id}>
                    <SuggestionCard
                      suggestion={suggestion}
                      slots={slots}
                      familyHex={familyHex}
                      occasionName={
                        suggestion.occasion_id
                          ? occasions.get(suggestion.occasion_id)
                          : undefined
                      }
                      onChange={replace}
                    />
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/** The piece every suggestion is built around, with a way back to all suggestions. */
function AnchorPiece({
  id,
  familyHex,
}: {
  id: string;
  familyHex: Map<string, string | null>;
}) {
  const item = useItem(id);
  if (!item.data) return null;
  const piece = item.data;
  return (
    <div className="flex items-center gap-3 rounded-lg bg-surface p-2 pr-4 sm:self-start">
      <span className="flex size-14 shrink-0 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full">
        <ItemPhoto
          photo={piece.photo}
          alt=""
          hex={piece.color_hex ?? familyHex.get(piece.color_primary)}
        />
      </span>
      <span className="min-w-0">
        <span className="block text-sm text-ink-soft">Built around</span>
        <span className="block truncate font-medium">{piece.display_name}</span>
      </span>
    </div>
  );
}
