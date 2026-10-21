import { type Browser, type Page, expect, test } from "@playwright/test";

import { deleteAccount, startDemo } from "./helpers";

// Things axe can't see: where Tab goes, whether focus shows, and whether dialogs hold focus.
test.describe.configure({ mode: "serial" });

let page: Page;

test.beforeAll(async ({ browser }: { browser: Browser }) => {
  page = await browser.newPage();
  await startDemo(page);
});

test.afterAll(async () => {
  await deleteAccount(page);
  await page.close();
});

/** What has focus, and whether it shows: an outline, or a ring drawn as a shadow. */
async function focused(target: Page) {
  return target.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    // Next.js's own badge, shown only in development, isn't part of the app.
    if (!el || el === document.body || el.tagName === "NEXTJS-PORTAL") {
      return null;
    }
    const style = getComputedStyle(el);
    const outline =
      style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0;
    const ring = style.boxShadow !== "none";
    const name =
      el.getAttribute("aria-label") ??
      el.textContent?.trim().slice(0, 40) ??
      el.tagName;
    return {
      name: `${el.tagName.toLowerCase()} "${name}"`,
      shows: outline || ring,
    };
  });
}

test("the first Tab offers to skip to the content", async () => {
  await page.goto("/home");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main#main")).toBeFocused();
});

for (const path of [
  "/home",
  "/wardrobe",
  "/outfits/new",
  "/shopping",
  "/settings",
]) {
  test(`every stop on ${path} shows where focus is`, async () => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const hidden = [];
    for (let stop = 0; stop < 30; stop += 1) {
      await page.keyboard.press("Tab");
      const now = await focused(page);
      if (now && !now.shows) hidden.push(now.name);
    }
    expect(hidden).toEqual([]);
  });
}

test("a dialog keeps focus inside and gives it back when it closes", async () => {
  await page.goto("/wardrobe");
  const opener = page.getByRole("button", { name: /Jump to/ });
  await opener.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Jump to" });
  await expect(dialog).toBeVisible();
  for (let stop = 0; stop < 8; stop += 1) {
    await page.keyboard.press("Tab");
    expect(
      await dialog.evaluate((node) => node.contains(document.activeElement)),
    ).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(opener).toBeFocused();
});

test("closing a coverage square's outfits returns to that square", async () => {
  await page.goto("/insights");
  const square = page
    .getByRole("button", { name: /good outfits?\. Open\.$/ })
    .first();
  await square.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(square).toBeFocused();
});
