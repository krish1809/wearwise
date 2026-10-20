// Shopping responses for component tests. Made up for tests; never shown to anyone.

import type { Analysis, Candidate, Gaps } from "@/lib/shopping";

export function makeCandidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    id: "c1",
    source: "manual",
    archetype_id: null,
    name: null,
    display_name: "Navy chinos",
    brand: null,
    url: null,
    image_url: null,
    size_label: null,
    price: 180000,
    currency: "INR",
    price_checked_at: "2026-10-18T10:00:00Z",
    target_price: null,
    category_id: "chinos",
    slot: "bottom",
    color_primary: "navy",
    color_secondary: null,
    color_hex: null,
    pattern: "solid",
    fabric: "cotton",
    fit: null,
    formality: 3,
    warmth: 1,
    seasons: [],
    status: "considering",
    notes: null,
    item_id: null,
    photo: null,
    verdict: null,
    created_at: "2026-10-18T10:00:00Z",
    updated_at: "2026-10-18T10:00:00Z",
    ...overrides,
  };
}

export function brief(id: string, display_name: string, slot = "top") {
  return {
    id,
    display_name,
    category_id: "casual_shirt",
    slot,
    color_primary: "navy",
    color_hex: null,
    status: "available",
    archived: false,
    photo: null,
  };
}

export function makeAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  const shirt = brief("shirt", "White shirt");
  const loafers = brief("loafers", "Brown loafers", "footwear");
  return {
    kind: "core",
    verdict: "buy",
    reasons: [
      {
        code: "verdict.opens",
        kind: "positive",
        text: "It gives you a first good outfit for college / everyday in winter.",
      },
      {
        code: "verdict.similar",
        kind: "caution",
        text: "Similar to your black chinos.",
      },
    ],
    new_outfits: 6,
    coverage_gain: 2.5,
    cells: [
      { occasion_id: "college", season: "summer", before: 12, added: 4 },
      { occasion_id: "college", season: "winter", before: 0, added: 3 },
    ],
    matches: [{ item: shirt, score: 0.82 }],
    closest: brief("black-chinos", "Black chinos", "bottom"),
    redundancy: 0.71,
    rescued: [],
    examples: [
      {
        template_id: "separates",
        pieces: [
          { item: shirt, candidate: false },
          { item: null, candidate: true },
          { item: loafers, candidate: false },
        ],
      },
    ],
    cost_per_new_outfit: 30000,
    projected: null,
    usual_spend: 200000,
    within_budget: true,
    engine_version: "1.2",
    ...overrides,
  };
}

export function makeGaps(overrides: Partial<Gaps> = {}): Gaps {
  return {
    needs_occasions: false,
    covered: false,
    gaps: [
      {
        staples: [
          {
            id: "white_sneakers",
            name: "White sneakers",
            category_id: "sneakers",
            slot: "footwear",
            color: "white",
            hex: "#FFFFFF",
            pattern: "solid",
            fabric: "leather",
            group_id: "footwear",
            usual_spend: null,
            on_list: false,
          },
        ],
        coverage_gain: 3.2,
        new_outfits: 4,
        cells: [{ occasion_id: "college", season: "summer", added: 4 }],
        reason: "4 new good outfits, for college / everyday in every season.",
      },
    ],
    ...overrides,
  };
}
