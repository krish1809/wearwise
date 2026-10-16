/** The list with the value added, or removed if it was there. Order of choosing is kept. */
export function toggle(values: readonly string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((existing) => existing !== value)
    : [...values, value];
}
