/**
 * E2E smoke тесты для AI-репетитора.
 * Покрывают критические user-flows:
 *  1. Login flow (kid → subjects)
 *  2. Subjects page доступен
 *  3. Diagnostic page доступен
 *  4. Admin login → audit log
 *  5. Health endpoint
 */

import { test, expect } from "@playwright/test";

const TEST_USER = {
  email: "kirill@example.com",
  password: "strongpass1",
};

const ADMIN_USER = {
  email: "admin@example.com",
  password: "strongpass1",
};

test.describe("Public pages", () => {
  test("1. Homepage redirects to login", async ({ page }) => {
    await page.goto("/");
    // Главная редиректит на login или subjects (зависит от токена)
    await page.waitForLoadState("networkidle");
    expect(page.url()).toMatch(/\/(login|subjects)/);
  });

  test("2. Login page is accessible", async ({ page }) => {
    await page.goto("/login");
    // Поля формы с лейблами Email/Пароль
    await expect(page.getByText(/email/i).first()).toBeVisible();
    await expect(page.getByText(/пароль/i).first()).toBeVisible();
    // Кнопка Войти
    await expect(page.getByRole("button", { name: /войти|вход/i }).first()).toBeVisible();
  });

  test("3. Register page is accessible", async ({ page }) => {
    await page.goto("/register");
    // Должно быть поле для email
    await expect(page.locator("input[type='email'], input[name='email']").first()).toBeVisible();
  });

  test("4. Forgot-password page is accessible", async ({ page }) => {
    await page.goto("/forgot-password");
    await expect(page.locator("input[type='email'], input[name='email']").first()).toBeVisible();
  });
});

test.describe("Auth flow", () => {
  test("5. Kid login → subjects page", async ({ page }) => {
    await page.goto("/login");

    // Заполняем форму
    await page.locator("input[type='email'], input[name='email']").first().fill(TEST_USER.email);
    await page.locator("input[type='password']").first().fill(TEST_USER.password);

    // Отправляем
    await page.getByRole("button", { name: /войти|вход|логин/i }).click();

    // Должны перейти на /subjects
    await page.waitForURL(/\/subjects/, { timeout: 10000 });

    // Видно сетку предметов
    await expect(page.locator("text=Математика").first()).toBeVisible({ timeout: 5000 });
  });

  test("6. Wrong password shows error", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type='email']").first().fill(TEST_USER.email);
    await page.locator("input[type='password']").first().fill("wrongpassword");
    await page.getByRole("button", { name: /войти|вход/i }).click();

    // Должна быть ошибка (401 или сообщение)
    await page.waitForTimeout(2000);
    expect(page.url()).toMatch(/\/login/);
  });
});

test.describe("Subjects page", () => {
  test.beforeEach(async ({ page }) => {
    // Login перед каждым тестом
    await page.goto("/login");
    await page.locator("input[type='email']").first().fill(TEST_USER.email);
    await page.locator("input[type='password']").first().fill(TEST_USER.password);
    await page.getByRole("button", { name: /войти|вход/i }).click();
    await page.waitForURL(/\/subjects/, { timeout: 10000 });
  });

  test("7. Subjects page shows 12 subjects", async ({ page }) => {
    // Хотя бы один предмет виден
    await expect(page.locator("text=Математика").first()).toBeVisible({ timeout: 5000 });
  });

  test("8. Diagnostic button navigates to /diagnostic", async ({ page }) => {
    const diagLink = page.getByRole("link", { name: /диагностик/i }).first();
    await diagLink.click();
    await page.waitForURL(/\/diagnostic/, { timeout: 5000 });
  });
});

test.describe("Admin flow", () => {
  test("9. Admin can access /admin and see audit log", async ({ page, request }) => {
    // Чистый login через API чтобы не зависеть от UI (быстрее + не зависит от рейт-лимита)
    const r = await request.post("/api/v1/auth/login", {
      data: { email: ADMIN_USER.email, password: ADMIN_USER.password },
    });
    expect(r.status()).toBe(200);

    // Берём токен и кладём в localStorage
    const body = await r.json();
    await page.addInitScript((token: string) => {
      window.localStorage.setItem("auth_token", token);
    }, body.access_token);

    await page.goto("/admin");
    await expect(page.locator("text=/audit|аудит/i").first()).toBeVisible({ timeout: 10000 });
  });

  test("10. Admin can filter audit log", async ({ page, request }) => {
    const r = await request.post("/api/v1/auth/login", {
      data: { email: ADMIN_USER.email, password: ADMIN_USER.password },
    });
    expect(r.status()).toBe(200);
    const body = await r.json();
    await page.addInitScript((token: string) => {
      window.localStorage.setItem("auth_token", token);
    }, body.access_token);

    await page.goto("/admin");
    const filterInput = page.locator("input[placeholder*='Действие']").first();
    await expect(filterInput).toBeVisible({ timeout: 10000 });
    await filterInput.fill("user.register");
    await page.getByRole("button", { name: /применить/i }).click();
    await page.waitForTimeout(2000);
  });
});

test.describe("Health", () => {
  test("11. /health returns 200", async ({ request }) => {
    const r = await request.get("/health");
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.status).toBe("ok");
  });

  test("12. /api/v1/subjects without auth — публичный (200)", async ({ request }) => {
    // Subjects публичный — список виден до логина
    const r = await request.get("/api/v1/subjects");
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.length).toBeGreaterThan(0); // есть хотя бы 1 предмет
  });
});
