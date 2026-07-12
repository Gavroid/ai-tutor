import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config для AI-репетитора.
 * Тесты идут через HTTPS (self-signed, мы отключаем проверку).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 2,
  reporter: "list",

  use: {
    baseURL: process.env.BASE_URL || "https://192.168.1.86",
    trace: "on-first-retry",
    ignoreHTTPSErrors: true, // self-signed cert
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
