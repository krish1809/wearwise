"use client";

import { MapPin } from "lucide-react";
import { useId, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { problemFrom } from "@/lib/api/errors";
import { type Place, searchPlaces } from "@/lib/weather";

/** A chosen place: its label and coordinates, or a name typed but not matched to a place. */
export type ChosenPlace = {
  label: string;
  latitude: number | null;
  longitude: number | null;
};

type PlaceSearchProps = {
  label: string;
  hint: string;
  value: ChosenPlace | null;
  onChange: (place: ChosenPlace | null) => void;
  error?: string;
};

/**
 * Find a town by name and pick the right one from the matches, so the forecast comes from
 * the right place ("Hyderabad, Telangana, India", not the one in Pakistan).
 */
export function PlaceSearch({
  label,
  hint,
  value,
  onChange,
  error,
}: PlaceSearchProps) {
  const [editing, setEditing] = useState(value === null);
  const [query, setQuery] = useState(value?.label ?? "");
  const [results, setResults] = useState<Place[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const inputId = useId();
  const hintId = useId();
  const resultsId = useId();

  async function search() {
    const text = query.trim();
    if (text.length < 2) {
      setProblem("Type at least two letters of the town's name.");
      return;
    }
    setProblem(null);
    setSearching(true);
    try {
      const found = await searchPlaces(text);
      setResults(found);
      if (found.length === 0)
        setProblem("No places match that name. Check the spelling.");
    } catch (failure) {
      setProblem(problemFrom(failure).message);
    } finally {
      setSearching(false);
    }
  }

  if (!editing && value) {
    return (
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">{label}</span>
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-2">
            <MapPin aria-hidden className="size-4 text-ink-soft" />
            {value.label}
          </span>
          <Button
            type="button"
            variant="secondary"
            className="px-3"
            onClick={() => {
              setEditing(true);
              setResults(null);
            }}
          >
            Change
          </Button>
          <Button
            type="button"
            variant="quiet"
            className="px-3"
            onClick={() => {
              onChange(null);
              setQuery("");
              setEditing(true);
            }}
          >
            Remove
          </Button>
        </div>
        {value.latitude === null && (
          <p className="text-sm text-ink-soft">
            Not matched to a place yet, so there&apos;s no forecast. Change it
            and choose from the results.
          </p>
        )}
        {error && <p className="text-sm text-skip">{error}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={inputId}>{label}</Label>
        <p id={hintId} className="text-sm text-ink-soft">
          {hint}
        </p>
        <div className="flex flex-wrap gap-2">
          <Input
            id={inputId}
            aria-describedby={hintId}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void search();
              }
            }}
            autoComplete="address-level2"
            maxLength={100}
            className="sm:max-w-xs"
          />
          <Button
            type="button"
            variant="secondary"
            loading={searching}
            onClick={() => void search()}
          >
            Find
          </Button>
          {value && (
            <Button
              type="button"
              variant="quiet"
              onClick={() => {
                setEditing(false);
                setResults(null);
                setProblem(null);
              }}
            >
              Cancel
            </Button>
          )}
        </div>
      </div>
      {problem && <Alert tone="error">{problem}</Alert>}
      {error && !problem && <p className="text-sm text-skip">{error}</p>}
      {results && results.length > 0 && (
        <fieldset className="flex flex-col gap-2">
          <legend id={resultsId} className="mb-2 text-sm font-medium">
            Which one?
          </legend>
          <RadioGroup
            aria-labelledby={resultsId}
            className="gap-3"
            onValueChange={(index) => {
              const place = results[Number(index)];
              onChange({
                label: place.label,
                latitude: place.latitude,
                longitude: place.longitude,
              });
              setEditing(false);
              setResults(null);
            }}
          >
            {results.map((place, index) => (
              <div
                key={place.label + index}
                className="flex items-center gap-3"
              >
                <RadioGroupItem
                  id={`${resultsId}-${index}`}
                  value={String(index)}
                />
                <Label
                  htmlFor={`${resultsId}-${index}`}
                  className="text-base font-normal"
                >
                  {place.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
        </fieldset>
      )}
    </div>
  );
}
