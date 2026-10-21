import path from "node:path";

import { type Page, expect, test } from "@playwright/test";

import { deleteAccount } from "./helpers";

// The five main journeys, in order, by one new person: sign up, add an item with a photo,
// build an outfit, get suggestions, and check a purchase. Then they delete their account,
// so a run against production leaves nothing behind.
test.describe.configure({ mode: "serial" });

const PASSWORD = "correct horse battery staple";
const HEADERS = { "X-Requested-With": "e2e" };
let page: Page;
let email: string;

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage();
  email = `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
});

test.afterAll(async () => {
  // Normally the last journey deletes the account; this catches a run that stopped early.
  await deleteAccount(page);
  await page.close();
});

async function addByApi(category: string, colour: string) {
  const made = await page.request.post("/api/v1/items", {
    headers: HEADERS,
    data: { category_id: category, color_primary: colour },
  });
  expect(made.status()).toBe(201);
}

test("a new person signs up", async () => {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByRole("button", { name: "Skip all" }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  // The occasions they dress for, as onboarding would ask.
  const set = await page.request.patch("/api/v1/profile", {
    headers: HEADERS,
    data: { occasion_ids: ["college"] },
  });
  expect(set.ok()).toBe(true);
});

test("they add an item with a photo", async () => {
  await page.goto("/wardrobe/new");
  await page
    .locator("input[type=file]")
    .first()
    .setInputFiles(path.join(__dirname, "fixtures", "navy-shirt.png"));
  // The colour is suggested from the photo.
  await expect(page.getByRole("button", { name: /^Navy/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByLabel("Category").selectOption("casual_shirt");
  await page.getByRole("button", { name: "Add item" }).click();
  await expect(page).toHaveURL(/\/wardrobe\/[0-9a-f-]{36}$/);
  await expect(
    page.getByRole("heading", { name: "Navy casual shirt" }),
  ).toBeVisible();
  await addByApi("chinos", "beige");
  await addByApi("loafers", "brown");
});

test("they build an outfit and save it", async () => {
  await page.goto("/outfits/new");
  const tray = page.getByRole("group", { name: "Show pieces for" });
  await page.getByRole("button", { name: "Add: Navy casual shirt" }).click();
  await tray.getByRole("button", { name: "Bottom" }).click();
  await page.getByRole("button", { name: "Add: Beige chinos" }).click();
  await tray.getByRole("button", { name: "Footwear" }).click();
  await page.getByRole("button", { name: "Add: Brown loafers" }).click();
  await expect(page.getByRole("meter", { name: "Outfit score" })).toBeVisible();
  await page.getByRole("button", { name: "Save outfit" }).click();
  await expect(page).toHaveURL(/\/outfits\/[0-9a-f-]{36}$/);
});

test("they get suggestions and like one", async () => {
  await page.goto("/outfits/suggest");
  await page.getByLabel("Occasion").selectOption("college");
  // The page suggests for the usual occasion as it opens; ask again for this one.
  await page.getByRole("button", { name: /^Suggest (outfits|again)$/ }).click();
  const like = page.getByRole("button", { name: /^Like / }).first();
  await like.click();
  await expect(like).toHaveText(/Liked/);
});

test("they check a purchase before buying it", async () => {
  await page.goto("/shopping/new");
  await page.getByLabel("Category").selectOption("chinos");
  await page.getByRole("button", { name: /^Olive/ }).click();
  await page.getByRole("button", { name: "Add to shopping list" }).click();
  await expect(page).toHaveURL(/\/shopping\/[0-9a-f-]{36}$/);
  await expect(page.getByText("Verdict")).toBeVisible();
  await expect(page.getByText(/^(Buy|Consider|Skip)$/).first()).toBeVisible();
});

test("they delete their account and everything in it", async () => {
  await page.goto("/settings");
  await page.getByRole("tab", { name: "Account" }).click();
  await page.getByRole("button", { name: "Delete account" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("textbox").fill(email);
  await dialog.getByRole("button", { name: "Delete account" }).click();
  await expect(page).toHaveURL(/\/$/);
  const me = await page.request.get("/api/v1/auth/me");
  expect(me.status()).toBe(401);
});
