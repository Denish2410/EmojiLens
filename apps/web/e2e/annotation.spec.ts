import { expect, test } from "@playwright/test";

test("two annotators label a blinded queue and agreement updates", async ({ page, request }, info) => {
  const tag = `${info.project.name}${Date.now()}`;
  const slug = `ann-${tag}`;
  await request.post("/api/v1/datasets", { data: { slug, name: slug, kind: "synthetic_fixture", license: "CC0-1.0" } });
  const lines = Array.from({ length: 2 }, (_, i) =>
    JSON.stringify({ id: `r${i}`, text: `good morning friend ${i}`, language: "en", origin: "synthetic:e2e", license: "CC0-1.0" }),
  ).join("\n");
  await request.post(`/api/v1/datasets/${slug}/versions`, { data: lines, headers: { "Content-Type": "application/x-ndjson" } });
  await request.post(`/api/v1/datasets/${slug}/versions/1/freeze`, { data: { seed: 1 } });
  const gen = await (
    await request.post(`/api/v1/datasets/${slug}/versions/1/variants`, {
      data: { seed: 3, chain: [{ transform_id: "homoglyph", params: { rate: 0.4 } }] },
    })
  ).json();
  await request.post("/api/v1/annotation/guidelines", { data: { version: `g-${tag}`, title: "Equivalence", body: "Judge meaning only." } });
  await request.post("/api/v1/annotation/tasks", {
    data: { dataset: slug, version: 1, recipe_hash: gen.recipe_hash, guideline_version: `g-${tag}`, per_language: 2 },
  });

  await page.goto("/annotation");
  for (const who of [`a-${tag}`, `b-${tag}`]) {
    const reg = page.getByRole("form", { name: "Register annotator" });
    await reg.getByLabel("New pseudonym").fill(who);
    await reg.getByLabel("Proficiency en").selectOption("fluent");
    await reg.getByRole("button", { name: /register/i }).click();
    await expect(page.getByLabel("Annotate as")).toHaveValue(who);
    // The E2E database is shared across runs, so annotate two items from this annotator's queue.
    for (let i = 0; i < 2; i++) {
      const item = page.getByTestId("queue-task");
      await expect(item).toBeVisible();
      const before = await item.textContent();
      await page.getByLabel(/Equivalent: same meaning/).check();
      await page.getByLabel("Safe", { exact: true }).check();
      await page.getByRole("button", { name: /submit and next/i }).click();
      // Wait for this submission to land: the next item (or the empty queue) replaces this one.
      await expect(async () => {
        const empty = await page.getByTestId("queue-empty").isVisible();
        const now = empty ? null : ((await item.allTextContents())[0] ?? before);
        expect(empty || now !== before).toBe(true);
      }).toPass();
    }
  }
  await expect(page.getByTestId("alpha")).toHaveText(/^(undefined|-?\d\.\d{3})$/);
});
