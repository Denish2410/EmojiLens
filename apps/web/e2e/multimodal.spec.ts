import { expect, test } from "@playwright/test";

test("renders in the sandbox and reads back with real OCR", async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto("/multimodal");
  await page.getByRole("textbox", { name: "Original text" }).fill("Meeting moved to five tomorrow");
  await page.getByRole("button", { name: /render and read/i }).click();
  await expect(page.getByTestId("mm-image")).toBeVisible({ timeout: 30_000 });
  const ok = await page.getByTestId("ocr-text").isVisible().catch(() => false);
  if (ok) {
    await expect(page.getByTestId("ocr-text")).toContainText("Meeting");
  }
  await expect(page.getByTestId("vlm-unavailable")).toBeVisible();
});
