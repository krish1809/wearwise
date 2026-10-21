// Errors in the browser, sent to the server so the owner sees them next to the server's own
// (only the page's path and the error; nothing about the account).

const MAX_PER_PAGE_LOAD = 5;
let sent = 0;

/** A fresh id for one request, which the server logs and shows with any error it returns. */
export function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Array.from({ length: 16 }, () =>
    Math.floor(Math.random() * 16).toString(16),
  ).join("");
}

export function reportError(error: unknown): void {
  // A loop of failures shouldn't become a flood of reports.
  if (sent >= MAX_PER_PAGE_LOAD || typeof window === "undefined") return;
  sent += 1;
  const found = error instanceof Error ? error : new Error(String(error));
  void fetch("/api/v1/client-errors", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "fetch",
    },
    body: JSON.stringify({
      message: found.message.slice(0, 2000) || "Unknown error",
      path: window.location.pathname.slice(0, 500),
      stack: found.stack?.slice(0, 10_000) ?? null,
    }),
    keepalive: true,
  }).catch(() => {
    // Reporting is best effort; the person already sees the error itself.
  });
}

/** For tests: forget how many were sent. */
export function resetReports(): void {
  sent = 0;
}
