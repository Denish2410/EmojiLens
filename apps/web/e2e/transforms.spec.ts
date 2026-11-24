import { expect, test } from "@playwright/test";

test("run a smuggling chain, verify reproducibility, and inspect the output", async ({ page }) => {
  await page.goto("/transforms");
  await page.getByLabel("Transformation to add").selectOption("unicode_smuggling");
  await page.getByRole("button", { name: /^Add$/ }).click();
  await page.getByRole("list", { name: "Chain steps" }).getByLabel("method").selectOption("tag_payload");
  await page.getByRole("button", { name: /run chain/i }).click();
  const hash = await page.getByTestId("chain-hash").textContent();
  expect(hash).toMatch(/^[0-9a-f]{64}$/);
  await expect(page.getByLabel("Transformed with invisible characters revealed")).toContainText("<U+E0053>");

  await page.getByRole("button", { name: /run chain/i }).click();
  await expect(page.getByTestId("chain-hash")).toHaveText(hash!);

  await page.getByRole("button", { name: /inspect output/i }).click();
  await page.getByRole("button", { name: /^Analyse$/ }).click();
  await expect(page.getByTestId("decoded-payload")).toHaveText("SURROGATE-TOKEN");
});

test("generate variants for a frozen dataset version", async ({ page, request }, info) => {
  const slug = `tv-${info.project.name}-${Date.now()}`;
  await request.post("/api/v1/datasets", {
    data: { slug, name: `Variants ${slug}`, kind: "synthetic_fixture", license: "CC0-1.0" },
  });
  const lines = Array.from({ length: 6 }, (_, i) =>
    JSON.stringify({ id: `r${i}`, text: `good morning friend ${i}`, language: "en", origin: "synthetic:e2e", license: "CC0-1.0" }),
  ).join("\n");
  await request.post(`/api/v1/datasets/${slug}/versions`, { data: lines, headers: { "Content-Type": "application/x-ndjson" } });
  await request.post(`/api/v1/datasets/${slug}/versions/1/freeze`, { data: { seed: 1 } });

  await page.goto("/transforms");
  await page.getByLabel("Transformation to add").selectOption("homoglyph");
  await page.getByRole("button", { name: /^Add$/ }).click();
  await page.getByLabel("Frozen version").selectOption(`${slug}@1`);
  await page.getByRole("button", { name: /generate variants/i }).click();
  await expect(page.getByTestId("generate-result")).toContainText("created 6");
});
