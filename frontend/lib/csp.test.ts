import { describe, expect, it } from "vitest";

import { contentSecurityPolicy } from "@/lib/csp";

function connectSrc(policy: string): string | undefined {
  return policy.split("; ").find((part) => part.startsWith("connect-src"));
}

describe("contentSecurityPolicy", () => {
  it("lets the browser call only this site when no wake-up address is set", () => {
    expect(connectSrc(contentSecurityPolicy({ dev: false }))).toBe(
      "connect-src 'self'",
    );
  });

  it("adds the backend's origin, and nothing more of its address, when it is set", () => {
    const policy = contentSecurityPolicy({
      dev: false,
      wakeUrl: "https://wearwise-api.example.test/some/path",
    });
    expect(connectSrc(policy)).toBe(
      "connect-src 'self' https://wearwise-api.example.test",
    );
  });

  it("keeps what hot reloading needs in development only", () => {
    expect(connectSrc(contentSecurityPolicy({ dev: true }))).toBe(
      "connect-src 'self' ws:",
    );
    expect(contentSecurityPolicy({ dev: false })).not.toContain("unsafe-eval");
  });
});
