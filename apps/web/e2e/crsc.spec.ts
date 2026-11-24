import { expect, test } from "@playwright/test";

test("CRSC analytics never shows metrics without a completed experiment", async ({ page, request }) => {
  const exps = await (await request.get("/api/v1/experiments")).json();
  await page.goto("/crsc");
  await expect(page.getByRole("heading", { name: /CRSC Analytics/ })).toBeVisible();
  await expect(page.getByText("experimental", { exact: true })).toBeVisible();
  if (!exps.some((e: { status: string }) => e.status === "completed")) {
    await expect(page.getByTestId("crsc-empty")).toBeVisible();
  }
});
