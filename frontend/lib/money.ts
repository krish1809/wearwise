// The API stores money as whole paise (1 rupee = 100 paise), so no amount is ever a fraction.

// Matches the backend's limit (backend/app/api/fields.py).
export const MAX_RUPEES = 10_000_000;

/** Rupees typed by the person, in paise; null when blank, NaN when not an amount. */
export function rupeesToPaise(text: string): number | null {
  const trimmed = text.trim().replaceAll(",", "");
  if (trimmed === "") return null;
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) return Number.NaN;
  return Math.round(Number(trimmed) * 100);
}

/** Paise as rupees for an input: "1500", or "1500.5" when there are paise. */
export function paiseToRupeesText(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "";
  return String(paise / 100);
}

/** Paise for reading: "₹1,500". */
export function formatRupees(paise: number): string {
  const digits = paise % 100 === 0 ? 0 : 2;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(paise / 100);
}

export const AMOUNT_ERROR = `Enter an amount in rupees, up to ₹${MAX_RUPEES.toLocaleString("en-IN")}.`;
