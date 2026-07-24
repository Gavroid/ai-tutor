import { test, expect } from "@playwright/test";

/**
 * Sprint 37: Production verify — комплексный smoke test для production.
 *
 * Запускается через:
 *   npx playwright test e2e/production-verify.spec.ts --workers=1 \
 *     --config baseURL=https://192.168.1.86
 *
 * Проверяет:
 * 1. Health endpoint
 * 2. Login flow (cookie auth)
 * 3. /api/v1/auth/me через cookie
 * 4. /api/v1/teacher/materials (после Sprint 36.1 fix)
 * 5. /api/v1/admin/audit-log
 * 6. /api/v1/student/streak
 * 7. /api/v1/ai/budget/usage
 */

test.describe.configure({ mode: "serial" });

test.describe("Sprint 37: Production verify @ 192.168.1.86", () => {
  test("API: /health endpoint", async ({ request }) => {
    const r = await request.get("/health");
    expect(r.ok()).toBe(true);
    expect(r.status()).toBe(200);
  });

  test("API: /ready endpoint", async ({ request }) => {
    const r = await request.get("/ready");
    expect(r.ok()).toBe(true);
    expect(r.status()).toBe(200);
  });

  test("API: /api/v1/subjects (без auth — public)", async ({ request }) => {
    const r = await request.get("/api/v1/subjects");
    // Sprint 37: /api/v1/subjects PUBLIC (список предметов не требует auth).
    expect(r.status()).toBe(200);
  });

  test("API: login → cookie (Sprint 27)", async ({ request }) => {
    const r = await request.post("/api/v1/auth/login", {
      data: { email: "kirill@example.com", password: "Kirill2026!" },
    });
    expect(r.status()).toBe(200);

    // Проверяем Set-Cookie header напрямую
    const setCookie = r.headers()["set-cookie"] || "";
    expect(setCookie).toMatch(/ai_tutor_access/);
    expect(setCookie).toMatch(/HttpOnly/i);
  });

  test("API: /me через cookie (Sprint 27 fix)", async ({ request }) => {
    // Login
    const loginR = await request.post("/api/v1/auth/login", {
      data: { email: "kirill@example.com", password: "Kirill2026!" },
    });
    expect(loginR.status()).toBe(200);

    // /me через cookie (БЕЗ Authorization header)
    const meR = await request.get("/api/v1/auth/me");
    expect(meR.status(), "/me should work via cookie").toBe(200);
    const me = await meR.json();
    expect(me.email).toBe("kirill@example.com");
  });

  test("API: /api/v1/student/streak (Sprint 8.1)", async ({ request }) => {
    // Sprint 37: streak требует auth (как student, так и parent).
    const loginR = await request.post("/api/v1/auth/login", {
      data: { email: "kirill@example.com", password: "Kirill2026!" },
    });
    expect(loginR.status()).toBe(200);
    const r = await request.get("/api/v1/student/streak");
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(typeof data.current_streak_days).toBe("number");
  });

  test("API: /api/v1/ai/budget/usage (Sprint 16.1)", async ({ request }) => {
    // Login first.
    await request.post("/api/v1/auth/login", {
      data: { email: "kirill@example.com", password: "Kirill2026!" },
    });
    const r = await request.get("/api/v1/ai/budget/usage");
    expect(r.status()).toBe(200);
  });

  test("API: admin login + /admin/stats (Sprint 9.2)", async ({ request }) => {
    // Login as admin
    const loginR = await request.post("/api/v1/auth/login", {
      data: { email: "admin@example.com", password: "Kirill2026!" },
    });
    expect(loginR.status()).toBe(200);

    const r = await request.get("/api/v1/admin/stats");
    expect(r.status()).toBe(200);
  });

  test("API: /admin/audit-log?limit=5 (Sprint 10.4)", async ({ request }) => {
    // Login
    await request.post("/api/v1/auth/login", {
      data: { email: "admin@example.com", password: "Kirill2026!" },
    });
    const r = await request.get("/api/v1/admin/audit-log?limit=5");
    expect(r.status()).toBe(200);
  });

  test("API: /api/v1/teacher/materials (Sprint 36.1 fix — 200, not 500)", async ({
    request,
  }) => {
    await request.post("/api/v1/auth/login", {
      data: { email: "admin@example.com", password: "Kirill2026!" },
    });
    const r = await request.get("/api/v1/teacher/materials?limit=10");
    // Sprint 36.1: до фикса был 500. Теперь 200.
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test("UI: Login page загружается", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /вход|войти/i })).toBeVisible({
      timeout: 10000,
    });
  });

  test("UI: /login → /subjects (Kirill)", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', "kirill@example.com");
    await page.fill('input[type="password"]', "Kirill2026!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(subjects|parents|teacher|admin)/, {
      timeout: 15000,
    });
    // Не должно быть редиректа обратно на /login
    expect(page.url()).not.toContain("/login");
  });

  test("UI: ThemeToggle кнопка присутствует", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByTestId("theme-toggle")).toBeVisible({
      timeout: 5000,
    });
  });
});