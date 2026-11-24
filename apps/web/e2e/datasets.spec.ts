import { expect, test } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.resolve(HERE, "../../../datasets/fixtures/benign_controls.synthetic.jsonl");

test("create, import, freeze and validate a dataset end to end", async ({ page }, info) => {
  const slug = `e2e-${info.project.name}-${Date.now()}`;
  await page.goto("/datasets");
  await page.getByRole("button", { name: /new dataset/i }).click();
  const form = page.getByRole("form", { name: "New dataset" });
  await form.getByLabel("Slug").fill(slug);
  await form.getByLabel("Name").fill("E2E benign controls");
  await form.getByLabel("Kind").selectOption("synthetic_fixture");
  await form.getByLabel("License").fill("CC0-1.0");
  await form.getByRole("button", { name: /create dataset/i }).click();
  await expect(page).toHaveURL(new RegExp(`/datasets/${slug}$`));

  await page.getByLabel(/import jsonl/i).setInputFiles(FIXTURE);
  await expect(page.getByTestId("content-hash")).toHaveText(/^[0-9a-f]{64}$/);
  await expect(page.getByRole("cell", { name: "benign-001", exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: /freeze splits/i }).click();
  await expect(page.getByTestId("leakage-ok")).toBeVisible();
  await expect(page.getByText("frozen", { exact: true })).toBeVisible();

  await page.getByLabel("Filter by language").selectOption("gu");
  await expect(page.getByText(/matching/)).toContainText(/^[1-9]\d* matching$/);
});

test("multilingual lab identifies Romanized Gujarati with CLDR meanings", async ({ page }) => {
  await page.goto("/multilingual");
  await page.getByRole("button", { name: "gu-Latn" }).click();
  await page.getByRole("button", { name: /^Analyse$/ }).click();
  await expect(page.getByTestId("variety-label")).toHaveText("Romanized Gujarati");
  await expect(page.getByText(/CLDR 49/)).toBeVisible();
  await expect(page.getByText(/fallback: gu/).first()).toBeVisible();
});
