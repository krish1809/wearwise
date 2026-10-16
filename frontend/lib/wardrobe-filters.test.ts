import { describe, expect, it } from "vitest";

import { categoriesFor, type Category } from "@/lib/wardrobe";
import {
  activeCount,
  cleared,
  filtersFrom,
  searchFrom,
  withToggled,
} from "@/lib/wardrobe-filters";

describe("filters in the address bar", () => {
  it("round-trips through the query string", () => {
    const filters = filtersFrom(
      new URLSearchParams(
        "q=navy&color=navy&color=black&season=summer&archived=1&sort=oldest",
      ),
    );

    expect(filters.color).toEqual(["navy", "black"]);
    expect(filters.archived).toBe(true);
    expect(searchFrom(filters)).toBe(
      "?q=navy&color=navy&color=black&season=summer&archived=1&sort=oldest",
    );
    expect(activeCount(filters)).toBe(3);
  });

  it("leaves defaults out and ignores an unknown sort", () => {
    const filters = filtersFrom(new URLSearchParams("sort=sideways"));

    expect(filters.sort).toBe("newest");
    expect(searchFrom(filters)).toBe("");
  });

  it("toggles one value and clears all but the search", () => {
    const start = filtersFrom(new URLSearchParams("q=tee&color=navy"));

    expect(withToggled(start, "color", "navy").color).toEqual([]);
    expect(withToggled(start, "color", "red").color).toEqual(["navy", "red"]);
    expect(searchFrom(cleared(withToggled(start, "status", "laundry")))).toBe(
      "?q=tee",
    );
  });
});

describe("categoriesFor", () => {
  const make = (id: string, sections: string[], custom = false): Category => ({
    id,
    name: id,
    group_id: "tops",
    slot: "top",
    sections,
    formality_default: 2,
    formality_min: 1,
    formality_max: 3,
    warmth: 1,
    wears_before_wash: 1,
    custom,
  });
  const all = [
    make("tshirt", ["menswear", "womenswear"]),
    make("blouse", ["womenswear"]),
    make("kurta_set", [], true),
  ];

  it("offers the sections shopped, and the person's own categories", () => {
    expect(categoriesFor(all, ["menswear"], false).map((c) => c.id)).toEqual([
      "tshirt",
      "kurta_set",
    ]);
  });

  it("offers everything with show all, or when no section was chosen", () => {
    expect(categoriesFor(all, ["menswear"], true)).toHaveLength(3);
    expect(categoriesFor(all, [], false)).toHaveLength(3);
  });
});
