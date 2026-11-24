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
  const cell = (name: string) => page.getByRole("cell", { name, exact: true });
  await expect(cell("ZERO WIDTH SPACE")).toBeVisible();
  await expect(cell("ZERO WIDTH JOINER").first()).toBeVisible();
  await expect(cell("ZERO WIDTH NON-JOINER")).toBeVisible();

  // The family emoji is one grapheme made of five code points.
  const family = page.getByRole("button", { name: /^Grapheme \d+$/ }).filter({ hasText: "👨" });
  await expect(family).toContainText("5");
});

test("reveals a concealed tag payload and keeps legitimate Indic joiners", async ({ page }) => {
  const hidden = Array.from("hello", (c) => String.fromCodePoint(0xe0000 + c.charCodeAt(0))).join("");
  const input = `Nice day${hidden} ક્\u200cષ`;

  await page.goto("/inspector");
  await page.getByRole("textbox", { name: "Original text" }).fill(input);
  await page.getByRole("button", { name: /^Analyse$/ }).click();

  await expect(page.getByTestId("decoded-payload")).toHaveText("hello");
  const findings = page.getByRole("list", { name: "Evidence findings" });
  await expect(findings).toContainText("tag.ascii_payload");
  await expect(findings).toContainText("indic.joiner_after_virama");
  await expect(findings).toContainText("Legitimate structure");

  // Sanitized view drops the tags but keeps the Gujarati ZWNJ.
  await expect(page.getByTestId("view-text")).toHaveText("Nice day ક્\u200cષ");
  await page.getByRole("tab", { name: /decoded/i }).click();
  await expect(page.getByTestId("view-text")).toContainText("⟦hello⟧");
});
