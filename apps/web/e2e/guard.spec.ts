import { expect, test } from "@playwright/test";

test("EmojiGuard flags a zero-width split and allows legitimate Gujarati", async ({ page }) => {
  await page.goto("/guard");
  await page.getByRole("textbox", { name: "Input" }).fill("reset your pass\u200bword now");
  await page.getByRole("button", { name: /^Assess$/ }).click();
  await expect(page.getByTestId("guard-recommendation")).toHaveText(/review|Flag/);
  await page.getByRole("textbox", { name: "Input" }).fill("ક્\u200cષ \u{1F44D}\u{1F3FD}");
  await page.getByRole("button", { name: /^Assess$/ }).click();
  await expect(page.getByTestId("guard-recommendation")).toHaveText(/^Allow/);
});

test("evaluation dashboard loads", async ({ page }) => {
  await page.goto("/evaluation");
  await expect(page.getByRole("heading", { name: "Evaluation Dashboard" })).toBeVisible();
});
