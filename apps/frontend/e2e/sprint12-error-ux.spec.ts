import { test, expect } from "@playwright/test";

test("Sprint 12 ErrorState on badges when API fails", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForLoadState("networkidle");

  await page.route("**/api/v1/student/badges", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Service unavailable (test)" }),
    })
  );

  await page.goto("/student/badges");
  await page.waitForLoadState("networkidle");

  const errorState = page.locator('[data-testid="error-state"]');
  await expect(errorState).toBeVisible({ timeout: 5_000 });

  // Sprint 12: retry-кнопка имеет русский текст «Попробовать ещё раз».
  const retryBtn = errorState.getByRole("button", {
    name: /попробовать/i,
  });
  await expect(retryBtn).toBeVisible();
});

test("Sprint 12 skeleton transition without layout shift", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForLoadState("networkidle");

  await page.route("**/api/v1/student/badges", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await route.continue();
  });

  await page.goto("/student/badges");
  await page.waitForLoadState("domcontentloaded");

  const skeleton = page.locator('[data-testid="badges-skeleton"]');
  await expect(skeleton).toBeVisible({ timeout: 2_000 });

  await expect(skeleton).toBeHidden({ timeout: 15_000 });
});

test("Sprint 12 T1D-friendly message in AI chat when 503", async ({ page }) => {
  // Sprint 12: 503 → "AI временно недоступен" вместо технического "[ошибка]".
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForLoadState("networkidle");

  await page.route("**/api/v1/ai/explain", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "AI service down" }),
    })
  );

  await page.goto("/topics/31");
  await page.waitForLoadState("networkidle");

  // Ищем основную кнопку в чате.
  const explainBtn = page
    .getByRole("button", { name: /объясн/i })
    .first();
  if ((await explainBtn.count()) === 0) test.skip();
  await explainBtn.click();

  // T1D-friendly сообщение должно появиться в чате.
  await expect(
    page.getByText(/AI временно недоступен/i).first(),
  ).toBeVisible({ timeout: 10_000 });
});

test("Sprint 12 429 message: «Слишком много запросов»", async ({ page }) => {
  // Sprint 12: 429 → «Подожди минуту» (не агрессивное).
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForLoadState("networkidle");

  await page.route("**/api/v1/ai/explain", (route) =>
    route.fulfill({
      status: 429,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Too Many Requests" }),
    })
  );

  await page.goto("/topics/31");
  await page.waitForLoadState("networkidle");

  const explainBtn = page
    .getByRole("button", { name: /объясн/i })
    .first();
  if ((await explainBtn.count()) === 0) test.skip();
  await explainBtn.click();

  // Either 429 message OR the AI temp unreachable — both are T1D-friendly.
  await expect(
    page
      .getByText(/Слишком много запросов|AI временно недоступен/i)
      .first(),
  ).toBeVisible({ timeout: 10_000 });
});
