// Wardrobe fixtures for component tests, named after rows in seed/taxonomy.json.

import type { Category, Item } from "@/lib/wardrobe";

export function makeCategory(overrides: Partial<Category> = {}): Category {
  return {
    id: "tshirt",
    name: "T-shirt",
    group_id: "tops",
    slot: "top",
    sections: ["menswear", "womenswear"],
    formality_default: 2,
    formality_min: 1,
    formality_max: 3,
    warmth: 1,
    wears_before_wash: 1,
    custom: false,
    ...overrides,
  };
}

export const CATEGORIES: Category[] = [
  makeCategory(),
  makeCategory({
    id: "sneakers",
    name: "Sneakers",
    group_id: "footwear",
    slot: "footwear",
    formality_default: 2,
    wears_before_wash: null,
  }),
  makeCategory({
    id: "blouse",
    name: "Blouse",
    sections: ["womenswear"],
    formality_default: 3,
  }),
];

export function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: "item-1",
    category_id: "tshirt",
    slot: "top",
    name: null,
    display_name: "Navy t-shirt",
    brand: null,
    size_label: null,
    color_primary: "navy",
    color_secondary: null,
    color_hex: null,
    pattern: "solid",
    fabric: null,
    fit: null,
    formality: 2,
    warmth: 1,
    seasons: [],
    occasion_ids: [],
    style_tags: [],
    price: null,
    currency: "INR",
    purchased_on: null,
    status: "available",
    wears_before_wash: 1,
    wears_since_wash: 0,
    set_id: null,
    notes: null,
    archived: false,
    created_at: "2026-10-13T10:00:00Z",
    updated_at: "2026-10-13T10:00:00Z",
    photo: null,
    set_members: [],
    wear_count: 0,
    last_worn_on: null,
    ...overrides,
  };
}
