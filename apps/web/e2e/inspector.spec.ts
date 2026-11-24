import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";

test("overview shows the real API as live and ready", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/API .* is live/)).toBeVisible();
  await expect(page.getByText(/journal_mode=wal/)).toBeVisible();
});

test("analyses Unicode input end to end and preserves it exactly", async ({ page }) => {
  const input = " Hi\u200b 👨\u200d👩\u200d👧 क्\u200dष ક્\u200cષ ";
  const expectedSha = createHash("sha256").update(Buffer.from(input, "utf8")).digest("hex");

  await page.goto("/inspector");
  await page.getByRole("textbox", { name: "Original text" }).fill(input);
  await page.getByRole("button", { name: /^Analyse$/ }).click();

  await expect(page.getByTestId("sha256")).toHaveText(expectedSha);
  await expect(page.getByText("ZERO WIDTH SPACE")).toBeVisible();
  await expect(page.getByText("ZERO WIDTH JOINER").first()).toBeVisible();
  await expect(page.getByText("ZERO WIDTH NON-JOINER")).toBeVisible();

  // The family emoji is one grapheme made of five code points.
  const family = page.getByRole("button", { name: /^Grapheme \d+$/ }).filter({ hasText: "👨" });
  await expect(family).toContainText("5");
});
