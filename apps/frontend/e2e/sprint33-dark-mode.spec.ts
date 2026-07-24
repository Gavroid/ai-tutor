import { test, expect } from "@playwright/test";

/**
 * Sprint 33: E2E тесты для dark mode.
 *
 * Проверяем:
 * 1. Default theme = light
 * 2. Toggle на dark → html.classList содержит 'dark'
 * 3. localStorage persist (после reload)
 * 4. FOUC prevention: html class установлен ДО hydration
 * 5. Toggle обратно на light → 'dark' убран
 */

test.describe("Sprint 33: Dark mode polish", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => localStorage.removeItem("ai-tutor:theme"));
  });

  test("default theme = light (после clear localStorage)", async ({ page }) => {
    await page.goto("/");
    const isDark = await page.evaluate(() =>
      document.documentElement.classList.contains("dark"),
    );
    expect(isDark).toBe(false);
  });

  test("toggle на dark → html.classList содержит 'dark'", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("theme-toggle").click();
    await page.waitForTimeout(100);
    const isDark = await page.evaluate(() =>
      document.documentElement.classList.contains("dark"),
    );
    expect(isDark).toBe(true);

    // localStorage сохраняет
    const saved = await page.evaluate(() =>
      localStorage.getItem("ai-tutor:theme"),
    );
    expect(saved).toBe("dark");
  });

  test("theme persists через reload", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("theme-toggle").click();
    await page.waitForTimeout(100);

    await page.reload();
    await page.waitForLoadState("domcontentloaded");

    // После reload class="dark" должен быть ДО hydration (FOUC prevention script)
    const isDarkAfterReload = await page.evaluate(() =>
      document.documentElement.classList.contains("dark"),
    );
    expect(isDarkAfterReload).toBe(true);
  });

  test("FOUC prevention script устанавливает class до React", async ({
    page,
  }) => {
    // Устанавливаем dark через localStorage
    await page.goto("/login");
    await page.evaluate(() => localStorage.setItem("ai-tutor:theme", "dark"));

    // Открываем страницу. Сразу проверяем class.
    await page.goto("/");
    const isDarkImmediate = await page.evaluate(() =>
      document.documentElement.classList.contains("dark"),
    );
    expect(isDarkImmediate).toBe(true);
  });

  test("toggle обратно на light → 'dark' убран из html", async ({ page }) => {
    await page.goto("/");
    // Сначала включим dark
    await page.getByTestId("theme-toggle").click();
    await page.waitForTimeout(100);
    let isDark = await page.evaluate(() =>
      document.documentElement.classList.contains("dark"),
    );
    expect(isDark).toBe(true);

    // Теперь обратно на light
    await page.getByTestId("theme-toggle").click();
    await page.waitForTimeout(100);
    isDark = await page.evaluate(() =>
      document.documentElement.classList.contains("dark"),
    );
    expect(isDark).toBe(false);

    const saved = await page.evaluate(() =>
      localStorage.getItem("ai-tutor:theme"),
    );
    expect(saved).toBe("light");
  });
});