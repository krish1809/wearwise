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
