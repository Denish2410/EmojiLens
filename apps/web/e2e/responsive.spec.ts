import { expect, test } from "@playwright/test";

const ROUTES = ["/", "/inspector", "/transforms", "/multilingual", "/datasets", "/annotation", "/models", "/experiments", "/crsc", "/multimodal", "/guard", "/evaluation", "/settings"];

// Elements wider than the viewport, ignoring content inside intentional scroll containers.
async function overflowing(page: import("@playwright/test").Page): Promise<string[]> {
  return page.evaluate(() => {
    const main = document.querySelector("main");
    return [...document.querySelectorAll("main *")]
      .filter((e) => {
        const r = e.getBoundingClientRect();
        if (r.width === 0) return false;
        for (let a = e.parentElement; a && a !== main; a = a.parentElement) {
          if (/(auto|scroll|hidden)/.test(getComputedStyle(a).overflowX)) return false;
        }
        return r.right > window.innerWidth + 1;
      })
      .map((e) => `${e.tagName}.${String(e.className).slice(0, 40)}`)
      .slice(0, 3);
  });
}

for (const route of ROUTES) {
  test(`no horizontal overflow on ${route}`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator("main h1").first()).toBeVisible();
    expect(await overflowing(page)).toEqual([]);
  });
}
