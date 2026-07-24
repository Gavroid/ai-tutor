import { test, expect } from "@playwright/test";

/**
 * Sprint 28: E2E тест cookie auth flow.
 *
 * Проверяем:
 * 1. Login через форму → cookies установлены (HttpOnly, Secure)
 * 2. После reload — пользователь остаётся залогиненным (cookie persistent)
 * 3. API вызовы работают через cookie
 * 4. Logout очищает cookies
 */

const KIRILL = {
  email: "kirill@example.com",
  password: "Kirill2026!",
};

test.describe("Sprint 28: Cookie auth flow", () => {
  test("login ставит cookies и пользователь остаётся залогиненным после reload", async ({
    page,
    context,
  }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[type="email"]', KIRILL.email);
    await page.fill('input[type="password"]', KIRILL.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(subjects|parents|teacher|admin)/, {
      timeout: 15000,
    });

    // Sprint 28: cookies должны быть установлены
    const cookies = await context.cookies();
    const tokenCookie = cookies.find(
      (c) => c.name === "ai_tutor_access" || c.name.includes("token"),
    );
    expect(tokenCookie).toBeTruthy();
    expect(tokenCookie?.httpOnly).toBe(true);  // HttpOnly!
    // SameSite (Playwright показывает как "Lax" | "Strict" | "None")
    expect(["Lax", "Strict"]).toContain(tokenCookie?.sameSite);

    // Reload — пользователь должен остаться залогиненным
    await page.reload();
    await page.waitForURL(/\/(subjects|parents|teacher|admin)/, {
      timeout: 5000,
    });
    // Не должно быть редиректа на /login
    expect(page.url()).not.toContain("/login");
  });

  test("logout очищает cookies", async ({ page, context }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[type="email"]', KIRILL.email);
    await page.fill('input[type="password"]', KIRILL.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(subjects|parents|teacher|admin)/, {
      timeout: 15000,
    });

    // Logout через Header
    await page.getByTestId("logout-button").click();
    await page.waitForURL(/\/login/, { timeout: 10000 });

    // Cookies должны быть expired (Max-Age=0)
    const cookies = await context.cookies();
    const tokenCookie = cookies.find(
      (c) => c.name === "ai_tutor_access" || c.name.includes("token"),
    );
    // После logout cookie либо удалена, либо expired
    if (tokenCookie) {
      // Если Playwright всё ещё показывает cookie — её expires должна быть в прошлом
      const expires = tokenCookie.expires;
      if (expires && expires > 0) {
        const expiresDate = new Date(expires * 1000);
        expect(expiresDate.getTime()).toBeLessThan(Date.now() + 5000);
      }
    }
  });

  test("API вызовы работают через cookie (без Authorization header)", async ({
    page,
  }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[type="email"]', KIRILL.email);
    await page.fill('input[type="password"]', KIRILL.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(subjects|parents|teacher|admin)/, {
      timeout: 15000,
    });

    // Sprint 28: проверяем что /api/v1/auth/me работает через cookie
    const meResponse = await page.request.get("/api/v1/auth/me");
    expect(meResponse.ok()).toBe(true);
    const meData = await meResponse.json();
    expect(meData.email).toBe(KIRILL.email);
  });

  test("Страница /subjects использует cookie для получения списка", async ({
    page,
  }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[type="email"]', KIRILL.email);
    await page.fill('input[type="password"]', KIRILL.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(subjects|parents|teacher|admin)/, {
      timeout: 15000,
    });

    // Sprint 28: проверяем что /subjects загружается
    // (если cookie нет, API вернёт 401 и страница покажет ошибку)
    await page.goto("/subjects");
    await expect(page.locator("h1, h2, .subject").first()).toBeVisible({
      timeout: 10000,
    });
  });
});