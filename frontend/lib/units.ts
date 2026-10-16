// Measurements are stored in centimetres and only shown in inches. Both are kept to one
// decimal place.

export type Units = "cm" | "in";

const CM_PER_INCH = 2.54;

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

/** A stored value in cm, as shown in the chosen units. */
export function fromCm(cm: number, units: Units): number {
  return round1(units === "cm" ? cm : cm / CM_PER_INCH);
}

/** A value typed in the chosen units, in cm for saving. */
export function toCm(value: number, units: Units): number {
  return round1(units === "cm" ? value : value * CM_PER_INCH);
}

/**
 * The allowed range in the chosen units, rounded inwards so that anything typed inside it
 * is still inside the range in cm.
 */
export function rangeIn(
  [low, high]: readonly [number, number],
  units: Units,
): [number, number] {
  if (units === "cm") return [low, high];
  return [
    Math.ceil((low / CM_PER_INCH) * 10) / 10,
    Math.floor((high / CM_PER_INCH) * 10) / 10,
  ];
}

/** Text typed into a number field, as a number; null when blank, NaN when not a number. */
export function parseNumber(text: string): number | null {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  return /^\d+([.,]\d+)?$/.test(trimmed)
    ? Number(trimmed.replace(",", "."))
    : Number.NaN;
}
