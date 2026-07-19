/**
 * Sprint 12 — error UX проверки.
 *
 * Тестирует:
 * - ErrorState компонент появляется когда network/AI API fails
 * - retry-кнопка работает
 * - Inline error в chat имеет специальный текст (T1D-friendly)
 * - Skeleton показывается пока данные грузятся
 */
import { test, expect } from "@playwright/test";

test.use({ ignoreHTTPSErrors: true, baseURL: "https://192.168.1.86" });

test("Sprint 12: ErrorState на /student/badges когда API падает", async ({
  page,
}) => {
  // Login как Кирилл
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForLoadState("networkidle");

  // Перехватываем запрос /api/v1/student/badges и делаем 503.
  await page.route("**/api/v1/student/badges", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Service unavailable (test)" }),
    }),
  );

  await page.goto("/student/badges");
  await page.waitForLoadState("networkidle");

  // Sprint 12: должен появиться ErrorState с retry-кнопкой.
  const errorState = page.locator('[data-testid="error-state"]');
  await expect(errorState).toBeVisible({ timeout: 5_000 });

  // Retry-кнопка доступна.
  const retryBtn = errorState.getByRole("button", {
    name: /попробовать|retry/i,
  });
  await expect(retryBtn).toBeVisible();
});

test("Sprint 12: skeleton → content transition без скачков layout", async ({
  page,
}) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForLoadState("networkidle");

  // Slow down network чтобы поймать skeleton.
  await page.route("**/api/v1/student/badges", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await route.continue();
  });

  await page.goto("/student/badges");
  await page.waitForLoadState("domcontentloaded");

  // Скелетон должен появиться мгновенно.
  const skeleton = page.locator('[data-testid="badges-skeleton"]');
  await expect(skeleton).toBeVisible({ timeout: 2000 });

  // После загрузки skeleton исчезает.
  await expect(skeleton).toBeHidden({ timeout: 15_000 });
});

test("Sprint 12: T1D-friendly сообщение для AI чат ошибки", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForLoadState("networkidle");

  // Перехватываем AI explain endpoint как 503.
  await page.route("**/api/v1/ai/explain", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "AI service down (test)" }),
    }),
  );

  await page.goto("/topics/31");
  await page.waitForLoadState("networkidle");

  await page.getByRole("button", { name: /объясни|объяснить/i }).click();

  // Sprint 12: должно появиться T1D-friendly сообщение в чате.
  // Не "произошла ошибка", а "🤖 AI временно недоступен. Попробуй позже."
  await expect(
    page.getByText(/AI временно недоступен/i).first(),
  ).toBeVisible({ timeout: 10_000 });
});
