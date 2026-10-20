import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

// Both themes' colour tokens, read from the stylesheet itself, checked against WCAG 2.2:
// 4.5:1 for text, 3:1 for the borders that show a control's edge.
const css = readFileSync(join(__dirname, "globals.css"), "utf8");

function tokens(block: string): Record<string, string> {
  return Object.fromEntries(
    [...block.matchAll(/--color-([a-z-]+):\s*(#[0-9a-f]{6})/gi)].map((m) => [
      m[1],
      m[2],
    ]),
  );
}

const light = tokens(
  css.slice(css.indexOf("@theme"), css.indexOf("--font-sans")),
);
const dark = {
  ...light,
  ...tokens(css.slice(css.indexOf(':root[data-theme="dark"]'))),
};

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (high + 0.05) / (low + 0.05);
}

const TEXT: [string, string][] = [
  ["ink", "paper"],
  ["ink", "surface"],
  ["ink", "tile"],
  ["ink-soft", "paper"],
  ["ink-soft", "surface"],
  ["ink-soft", "tile"],
  ["indigo", "paper"],
  ["indigo", "surface"],
  ["buy", "surface"],
  ["consider", "surface"],
  ["skip", "surface"],
  ["on-ink", "ink"],
  ["on-ink", "skip"],
  ["on-ink", "indigo"],
];
const EDGES: [string, string][] = [
  ["line-strong", "surface"],
  ["line-strong", "paper"],
];

describe.each([
  ["light", light],
  ["dark", dark],
])("the %s theme", (_, theme) => {
  it.each(TEXT)("%s text on %s reads at 4.5:1 or more", (text, background) => {
    expect(contrast(theme[text], theme[background])).toBeGreaterThanOrEqual(
      4.5,
    );
  });

  it.each(EDGES)("%s edges on %s show at 3:1 or more", (edge, background) => {
    expect(contrast(theme[edge], theme[background])).toBeGreaterThanOrEqual(3);
  });
});

it("the dark theme redefines every colour that changes role", () => {
  for (const name of Object.keys(light)) {
    if (["white", "on-light"].includes(name)) continue;
    expect(dark[name], name).not.toBe(light[name]);
  }
});
