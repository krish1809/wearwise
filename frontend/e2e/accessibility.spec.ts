import AxeBuilder from "@axe-core/playwright";
import { type Page, expect, test } from "@playwright/test";

import { deleteAccount, startDemo } from "./helpers";

// WCAG 2.1 A and AA, as axe checks them. Contrast is also measured for every token pair in
// app/theme.test.ts; this catches what only a rendered page shows.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
const THEMES = ["light", "dark"] as const;

const PUBLIC = [
  "/",
  "/login",
  "/register",
  "/privacy",
  "/forgot-password",
  "/unsubscribe",
];
const SIGNED_IN = [
  "/home",
  "/wardrobe",
  "/wardrobe/colours",
  "/outfits",
  "/outfits/new",
  "/outfits/suggest",
  "/outfits/remix",
  "/week",
  "/laundry",
  "/trips",
  "/shopping",
  "/shopping/plan",
  "/picks",
  "/insights",
  "/guide",
  "/settings",
];

async function chooseTheme(page: Page, theme: (typeof THEMES)[number]) {
  await page.evaluate((choice) => {
    localStorage.setItem("wearwise-theme", choice);
  }, theme);
}

async function problemsOn(page: Page, path: string, theme: string) {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
  // The page itself, not a redirect to log in, fully drawn, in the theme asked for.
  expect(new URL(page.url()).pathname).toBe(path);
  await expect(page.locator("h1").first()).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  expect(results.passes.length).toBeGreaterThan(10);
  // The design system's rule: no sideways scrolling, even on a phone.
  const sideways = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  );
  const wide =
    sideways > 0
      ? [`${path} (${theme}): ${sideways}px wider than the screen`]
      : [];
  return [
    ...wide,
    ...results.violations.map(
      (v) =>
        `${path} (${theme}): ${v.id} (${v.impact}): ${v.help}\n  ${v.nodes
          .slice(0, 3)
          .map((n) => n.target.join(" "))
          .join("\n  ")}`,
    ),
  ];
}

test("pages anyone can open have no accessibility problems", async ({
  page,
}) => {
  await page.goto("/");
  const problems = [];
  for (const theme of THEMES) {
    await chooseTheme(page, theme);
    for (const path of PUBLIC) {
      problems.push(...(await problemsOn(page, path, theme)));
    }
  }
  expect(problems).toEqual([]);
});

test("the app's pages have no accessibility problems", async ({ page }) => {
  // One demo for both themes, so a run makes as few accounts as it can.
  await startDemo(page);
  const problems = [];
  // One item's own page too.
  const listed = await page.request.get("/api/v1/items?limit=1");
  const [item] = ((await listed.json()) as { items: { id: string }[] }).items;
  const pages = [...SIGNED_IN, `/wardrobe/${item.id}`];
  try {
    for (const theme of THEMES) {
      await chooseTheme(page, theme);
      for (const path of pages) {
        problems.push(...(await problemsOn(page, path, theme)));
      }
    }
  } finally {
    await deleteAccount(page);
  }
  expect(problems).toEqual([]);
});
