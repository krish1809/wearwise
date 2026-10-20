import { readdirSync } from "node:fs";
import path from "node:path";

import { expect, it } from "vitest";

import { config } from "./proxy";

it("sends every logged-in page to log in first when there's no session", () => {
  const sections = ["(app)", "(onboarding)"].flatMap((group) =>
    readdirSync(path.join(__dirname, "app", group), { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name),
  );

  expect(sections.length).toBeGreaterThan(0);
  for (const section of sections) {
    expect(config.matcher).toContain(`/${section}/:path*`);
  }
});
