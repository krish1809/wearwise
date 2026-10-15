import { expect, it } from "vitest";

import { listed } from "@/lib/text";

it("joins names the way a sentence would", () => {
  expect(listed([])).toBe("");
  expect(listed(["Navy shirt"])).toBe("Navy shirt");
  expect(listed(["Black dress", "White sneakers"])).toBe(
    "Black dress and white sneakers",
  );
  expect(listed(["Navy shirt", "Olive chinos", "Brown loafers"])).toBe(
    "Navy shirt, olive chinos and brown loafers",
  );
});
