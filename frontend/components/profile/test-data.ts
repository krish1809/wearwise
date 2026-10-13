// A small slice of the reference lists in seed/, and an empty profile, for component tests.

import type { Profile, Reference } from "@/lib/profile";
import { apiAnswer } from "@/lib/test-utils";

export const REFERENCE: Reference = {
  sections: [
    { id: "menswear", name: "Menswear" },
    { id: "womenswear", name: "Womenswear" },
  ],
  fits: [
    { id: "slim", name: "Slim" },
    { id: "regular", name: "Regular" },
  ],
  sizing_systems: [
    { id: "in_uk", name: "IN / UK" },
    { id: "eu", name: "EU" },
  ],
  category_groups: [
    { id: "tops", name: "Tops" },
    { id: "footwear", name: "Footwear" },
  ],
  color_families: [
    { id: "navy", name: "Navy", hex: "#1F2A44", neutrality: 0.9 },
    { id: "orange", name: "Orange", hex: "#E07B2A", neutrality: 0 },
    { id: "multi", name: "Multicolour", hex: null, neutrality: 0 },
  ],
  occasions: [
    {
      id: "college",
      name: "College / everyday",
      formality_min: 1,
      formality_max: 3,
      hint: null,
    },
  ],
  style_profiles: [
    {
      id: "minimal",
      name: "Minimal",
      description: "Few colours, clean lines.",
      palette: ["navy"],
    },
  ],
};

export function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    sections: [],
    city: null,
    units: "cm",
    currency: "INR",
    height_cm: null,
    measurements: {},
    sizes: {},
    fit_preference: null,
    style_profile_ids: [],
    preferred_colors: [],
    avoided_colors: [],
    occasion_ids: [],
    budget_monthly: null,
    category_budgets: {},
    onboarding_step: 0,
    onboarding_skipped: false,
    show_onboarding_reminder: false,
    ...overrides,
  };
}

/** A mocked PATCH /profile that answers with the profile plus whatever was sent. */
export function echoProfilePatch(profile: Profile) {
  return (async (_path: string, init?: { body?: object }) =>
    apiAnswer(200, { ...profile, ...init?.body })) as never;
}
