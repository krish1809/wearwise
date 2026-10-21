import { type Page, expect } from "@playwright/test";

/** A fresh demo wardrobe, logged in, through the landing page's button. */
export async function startDemo(
  page: Page,
  section: "menswear" | "womenswear" = "menswear",
): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "Try the demo" }).click();
  await page.getByRole("menuitem", { name: `A ${section} wardrobe` }).click();
  await expect(page).toHaveURL(/\/home$/);
}

/** Delete the account the page is logged in as, so tests leave nothing behind. */
export async function deleteAccount(page: Page): Promise<void> {
  const me = await page.request.get("/api/v1/auth/me");
  if (!me.ok()) return;
  const { email } = (await me.json()) as { email: string };
  const deleted = await page.request.post("/api/v1/account/delete", {
    headers: { "X-Requested-With": "e2e" },
    data: { confirm_email: email },
  });
  expect(deleted.status()).toBe(204);
}
