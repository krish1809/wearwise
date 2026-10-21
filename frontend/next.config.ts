import type { NextConfig } from "next";

// The browser only talks to this app. Requests to /api/* are forwarded to the backend, so the
// session cookie (M1) stays first-party and no CORS setup is needed.
// Locally and in CI the backend is on localhost. On Vercel (which sets VERCEL during builds) a
// missing BACKEND_URL would quietly point the live site at localhost, so the build stops instead.
const backendUrl =
  process.env.BACKEND_URL ??
  (process.env.VERCEL ? undefined : "http://localhost:8000");

if (!backendUrl) {
  throw new Error(
    "BACKEND_URL is not set. Set it to the backend's address; on Vercel, under Project Settings > Environment Variables.",
  );
}

const dev = process.env.NODE_ENV === "development";

// Next.js puts its page data in inline scripts, so scripts may be inline; but they may only
// come from this site, nothing can frame it, and forms post only here (D49). Development adds
// what hot reloading needs. Shop pictures come from the shops' own addresses, so any https
// image is allowed.
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self'",
  `connect-src 'self'${dev ? " ws:" : ""}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains",
  },
];

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl.replace(/\/+$/, "")}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
