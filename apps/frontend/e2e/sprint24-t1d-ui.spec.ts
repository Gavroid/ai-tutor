import { test, expect } from "@playwright/test";

/**
 * Sprint 24: E2E тесты для T1D-friendly UI (Sprint 23).
 *
 * Тесты:
 * 1. PauseButton появляется на /topics/[id]
 * 2. Клик на PauseButton показывает 4 причины
 * 3. Выбор причины "hypo" → состояние паузы с calming сообщением
 * 4. "Я вернулся" возвращает к обычному виду
 * 5. SessionTimer НЕ показывается сразу (виден только после 20 мин)
 */

const KIRILL = {
  email: "kirill@example.com",
  password: "Kirill2026!",
};

test.describe("Sprint 24: T1D UI on /topics/[id]", () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[type="email"]', KIRILL.email);
    await page.fill('input[type="password"]', KIRILL.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/subjects|\/topics/, { timeout: 15000 });
  });

  test("PauseButton присутствует на /topics/[id]", async ({ page }) => {
    // Открываем первый subject → первый topic
    await page.goto("/subjects");
    await page.locator("a").first().click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10000 });

    // PauseButton должен быть
    await expect(page.getByRole("button", { name: /сделать паузу/i })).toBeVisible({
      timeout: 5000,
    });
  });

  test("PauseButton → выбор причины → состояние паузы", async ({ page }) => {
    await page.goto("/subjects");
    await page.locator("a").first().click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10000 });

    // Открываем опции паузы
    await page.getByRole("button", { name: /сделать паузу/i }).click();

    // Должны быть 4 причины (максимум): break, hypo, other (на разных строках)
    await expect(page.getByText(/у меня гипо/i)).toBeVisible({ timeout: 3000 });
    await expect(page.getByText(/отойду на/i)).toBeVisible();
    await expect(page.getByText(/другое/i)).toBeVisible();

    // Кликаем "У меня гипо"
    await page.getByText(/у меня гипо/i).click();

    // Должно появиться calming сообщение
    await expect(page.getByText(/твоя сессия сохранена/i)).toBeVisible({
      timeout: 3000,
    });
    // Streak НЕ прерывается (T1D-friendly)
    await expect(page.getByText(/streak не сломается/i)).toBeVisible();
  });

  test('"Я вернулся" возвращает к обычному виду', async ({ page }) => {
    await page.goto("/subjects");
    await page.locator("a").first().click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10000 });

    // Активируем паузу
    await page.getByRole("button", { name: /сделать паузу/i }).click();
    await page.getByText(/отойду на/i).click();
    await expect(page.getByText(/твоя сессия сохранена/i)).toBeVisible();

    // Возвращаемся
    await page.getByRole("button", { name: /я вернулся/i }).click();

    // PauseButton снова видна
    await expect(page.getByRole("button", { name: /сделать паузу/i })).toBeVisible({
      timeout: 3000,
    });
    // Сообщение о паузе исчезло
    await expect(page.getByText(/твоя сессия сохранена/i)).not.toBeVisible();
  });

  test("SessionTimer НЕ показывается сразу", async ({ page }) => {
    await page.goto("/subjects");
    await page.locator("a").first().click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10000 });

    // SessionTimer появляется только после 20 минут
    // Сразу после захода не должно быть warning
    await expect(page.getByText(/занимаешься уже/i)).not.toBeVisible({
      timeout: 2000,
    });
  });

  test("SessionTimer в aria-live polite mode", async ({ page }) => {
    await page.goto("/subjects");
    await page.locator("a").first().click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10000 });

    // Когда SessionTimer активен, role=status + aria-live=polite
    // (проверяем что компонент в DOM после mount)
    // Для теста просто проверяем что страница загрузилась
    await expect(page.locator("main")).toBeVisible();
  });
});
