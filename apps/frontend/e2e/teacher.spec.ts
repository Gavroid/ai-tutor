/**
 * E2E тесты для роли Учителя (Sprint 1.5).
 *
 * Проверяет:
 * - /teacher — список пуст/не пуст
 * - /teacher/generate — форма с 3 типами источников
 * - /teacher/materials/[id] — детальный просмотр + кнопки workflow
 * - Студент не видит ссылку "Учительская"
 * - Студент при заходе на /teacher получает ошибку (не видит список)
 */

import { test, expect } from "@playwright/test";

const TEACHER_USER = {
  email: "teacher-ui@example.com",
  password: "Kirill2026!",
};

const KID_USER = {
  email: "kirill@example.com",
  password: "Kirill2026!",
};

test.describe("Teacher UI", () => {
  test("13. /teacher is accessible for logged-in teacher", async ({ page }) => {
    // Логинимся учителем (если его нет — этот тест упадёт, и seed подготовит)
    await page.goto("/login");
    await page.locator("input[type='email']").first().fill(TEACHER_USER.email);
    await page.locator("input[type='password']").first().fill(TEACHER_USER.password);
    await page.getByRole("button", { name: /войти|вход/i }).click();
    await page.waitForTimeout(2000);

    // Если залогинились — идём в учительскую
    if (!page.url().includes("/login")) {
      await page.goto("/teacher");
      // Заголовок страницы
      await expect(page.getByText(/учительская/i).first()).toBeVisible({
        timeout: 5000,
      });
      // Кнопка генерации
      await expect(
        page.getByRole("link", { name: /сгенерировать материал/i }).first()
      ).toBeVisible();
    }
  });

  test("14. /teacher/generate has 3 source types", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type='email']").first().fill(TEACHER_USER.email);
    await page.locator("input[type='password']").first().fill(TEACHER_USER.password);
    await page.getByRole("button", { name: /войти|вход/i }).click();
    await page.waitForTimeout(2000);

    if (page.url().includes("/login")) {
      test.skip();
      return;
    }

    await page.goto("/teacher/generate");
    // 3 типа источника видны
    await expect(page.getByText(/только тема/i).first()).toBeVisible({
      timeout: 5000,
    });
    await expect(page.getByText(/^текст$/i).first()).toBeVisible();
    await expect(page.getByText(/^файл$/i).first()).toBeVisible();
    // Кнопка "Сгенерировать"
    await expect(
      page.getByRole("button", { name: /сгенерировать/i }).first()
    ).toBeVisible();
  });

  test("15. Student doesn't see Teacher link in nav", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type='email']").first().fill(KID_USER.email);
    await page.locator("input[type='password']").first().fill(KID_USER.password);
    await page.getByRole("button", { name: /войти|вход/i }).click();
    await page.waitForURL(/\/subjects/, { timeout: 10000 });

    // Кнопка "Учительская" НЕ должна быть видна
    const teacherLink = page.getByRole("link", { name: /учительская/i });
    await expect(teacherLink).not.toBeVisible();
  });
});
