// @ts-check
import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for DBOps Control Center E2E tests.
 *
 * The frontend dev server (Vite) is expected on port 5173 and the backend
 * API server on port 8000.  Adjust the env vars below or override with a
 * `.env` file when running in a different environment.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,          // run tests sequentially – they share backend state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "html",
  timeout: 60_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: process.env.BASE_URL || "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  /* Start the Vite dev server before tests if not already running. */
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
