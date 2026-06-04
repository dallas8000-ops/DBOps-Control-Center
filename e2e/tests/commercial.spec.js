import { test, expect } from "@playwright/test";

test("landing page shows hero and pricing", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /under control/i })).toBeVisible();
  await expect(page.getByText("Simple, transparent pricing.")).toBeVisible();
  await expect(page.getByText("Starter", { exact: true })).toBeVisible();
  await expect(page.getByText("Pro", { exact: true })).toBeVisible();
});

test("landing page links to terms of service", async ({ page, context }) => {
  await page.goto("/");
  const popupPromise = context.waitForEvent("page");
  await page.getByText("Terms of Service").click();
  const termsPage = await popupPromise;
  await expect(termsPage).toHaveURL(/terms-of-service\.html/);
  await expect(termsPage.getByText("Version 1.2")).toBeVisible();
  await expect(termsPage.getByText(/next billing cycle/i)).toBeVisible();
});

test("terms page is reachable directly", async ({ page }) => {
  await page.goto("/terms-of-service.html");
  await expect(page.getByRole("heading", { name: "Terms of Service" })).toBeVisible();
  await expect(page.getByText("Acceptance:")).toBeVisible();
});
