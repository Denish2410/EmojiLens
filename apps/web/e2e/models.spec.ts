import { expect, test } from "@playwright/test";

test("model arena shows the real catalogue and refuses to simulate missing models", async ({ page }) => {
  await page.goto("/models");
  const models = page.getByRole("list", { name: "Models" });
  await expect(models).toContainText("embed-multilingual-minilm");
  await expect(models).toContainText("tesseract-ocr");
  await expect(models).not.toContainText("test-double");
  await page.getByRole("radio", { name: "EMBED" }).click();
  await expect(page.getByTestId("no-models")).toContainText("Nothing is simulated");
});

test("experiment studio offers only installed text models", async ({ page }) => {
  await page.goto("/experiments");
  await expect(page.getByTestId("no-available-models")).toBeVisible();
  await expect(page.getByRole("button", { name: /queue experiment/i })).toBeDisabled();
});
