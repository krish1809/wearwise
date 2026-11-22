/**
 * The Content-Security-Policy header, built from settings so it can be tested.
 *
 * Next.js puts its page data in inline scripts, so scripts may be inline; but they may only
 * come from this site, nothing can frame it, and forms post only here (D49). Development adds
 * what hot reloading needs. Shop pictures come from the shops' own addresses, so any https
 * image is allowed. The browser may also call the backend's own address, only to wake it
 * (see lib/api/waking.ts); everything else goes through this site.
 */
export function contentSecurityPolicy({
  dev,
  wakeUrl,
}: {
  dev: boolean;
  wakeUrl?: string;
}): string {
  const connect = ["'self'"];
  if (wakeUrl) connect.push(new URL(wakeUrl).origin);
  if (dev) connect.push("ws:");
  return [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self'",
    `connect-src ${connect.join(" ")}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
}
