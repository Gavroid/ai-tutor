import { test, expect } from "@playwright/test";

test("Sprint 15 input has maxLength and counter", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), {
    timeout: 15_000,
  });
  await page.goto("/topics/31");
  await page.waitForLoadState("domcontentloaded");

  const input = page.locator(
    'input[placeholder*="Задай вопрос"]',
  );
  await expect(input).toBeVisible({ timeout: 5_000 });

  // Sprint 15.1: maxLength=500
  const maxLen = await input.getAttribute("maxlength");
  expect(maxLen).toBe("500");

  // Sprint 15.1: counter {input.length}/500
  await input.fill("Привет");
  await expect(page.getByText(/4\/500/)).toBeVisible({ timeout: 2_000 });
});

test("Sprint 15 typing updates counter live", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), {
    timeout: 15_000,
  });
  await page.goto("/topics/31");
  await page.waitForLoadState("domcontentloaded");

  const input = page.locator(
    'input[placeholder*="Задай вопрос"]',
  );
  await input.fill("Тестовый вопрос");

  // Counter должен показать "14/500" (Тестовый вопрос = 14 chars)
  await expect(page.getByText(/14\/500/)).toBeVisible({ timeout: 2_000 });
});
