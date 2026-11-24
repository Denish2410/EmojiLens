import { defineConfig, devices } from "@playwright/test";

// E2E tests run against the real API and the Vite dev server (no mocks).
// Set PLAYWRIGHT_CHROME_PATH to use a preinstalled Chromium/Chrome binary.
const executablePath = process.env.PLAYWRIGHT_CHROME_PATH;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    launchOptions: executablePath ? { executablePath } : {},
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: "EMOJILENS_DATABASE_URL=sqlite:///$(pwd)/../../var/e2e.db ../../scripts/dev-api.sh",
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "pnpm dev --host 127.0.0.1",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
