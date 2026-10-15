// Days as the person sees them: their own calendar, not the server's (which runs on UTC).

/** Today in the browser's time zone, as YYYY-MM-DD. */
export function todayIso(now: Date = new Date()): string {
  return isoDay(now);
}

export function isoDay(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

/** "Today", "Yesterday", or "Mon 12 Oct" (with the year when it isn't this year). */
export function dayLabel(iso: string, now: Date = new Date()): string {
  const today = todayIso(now);
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (iso === today) return "Today";
  if (iso === isoDay(yesterday)) return "Yesterday";
  const date = new Date(`${iso}T00:00:00`);
  return date.toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    ...(date.getFullYear() === now.getFullYear() ? {} : { year: "numeric" }),
  });
}

/** For the middle of a sentence: "today", "yesterday", or "on Mon, 12 Oct". */
export function dayPhrase(iso: string, now: Date = new Date()): string {
  const label = dayLabel(iso, now);
  return label === "Today" || label === "Yesterday"
    ? label.toLowerCase()
    : `on ${label}`;
}
