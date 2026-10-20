import { type NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/session";

// A quick first check before a logged-in page loads: without a session cookie, go to log in
// and come back afterwards. The API checks the session itself on every request; this only
// saves loading a page that can't show anything.
export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();
  const login = new URL("/login", request.url);
  login.searchParams.set(
    "next",
    request.nextUrl.pathname + request.nextUrl.search,
  );
  return NextResponse.redirect(login);
}

export const config = {
  matcher: [
    "/home/:path*",
    "/wardrobe/:path*",
    "/outfits/:path*",
    "/worn/:path*",
    "/week/:path*",
    "/laundry/:path*",
    "/trips/:path*",
    "/insights/:path*",
    "/shopping/:path*",
    "/guide/:path*",
    "/stylist/:path*",
    "/settings/:path*",
    "/onboarding/:path*",
  ],
};
