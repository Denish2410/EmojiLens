import { expect, test } from "@playwright/test";

test("overview dashboard reads stored counts from the real API", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/API .* is live/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Research readiness" })).toBeVisible();
  await expect(page.getByTestId("readiness-evaluation_dataset")).toBeVisible();
  await expect(page.getByLabel("Source records by language variety")).toContainText("gu-Latn");
});

test("settings shows system facts without filesystem paths", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Models and pinned revisions" })).toBeVisible();
  await expect(page.getByText(/\(head 00\d\d_m\d_/)).toBeVisible();
  const body = await page.locator("main").innerText();
  expect(body).not.toMatch(/\/home\/|\/Users\/|sqlite:\/\//);
});
