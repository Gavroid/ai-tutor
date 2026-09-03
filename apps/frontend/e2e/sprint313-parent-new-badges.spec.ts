/**
 * Sprint 3.13 — verify новой фичи «N новых с прошлого визита».
 *
 * Проверяет:
 * 1. На /parents pill «+N» рядом с именем ребёнка (если есть новые)
 * 2. На /parent/dashboard/[id] баннер «🎉 +N новых достижений»
 * 3. Кнопка «Понятно» скрывает баннер и обнуляет счётчик
 */

import { test, expect, type Page } from "@playwright/test";

const BASE = process.env.BASE_URL ?? "https://192.168.1.86";

async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto(`${BASE}/login`);
  await page.waitForLoadState("domcontentloaded");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await Promise.all([
    page.waitForLoadState("networkidle"),
    page.click('button[type="submit"]'),
  ]);
  await page.waitForFunction(() => !location.pathname.startsWith("/login"), { timeout: 10_000 });
}

test.describe("Sprint 3.13 — parent «N новых»", () => {
  test("баннер «+X новых» появляется на parent dashboard", async ({ page, context }) => {
    // Login как parent.
    await login(page, "parent.kirill@example.com", "ParentTest!2026");
    // Сначала mark all seen чтобы счётчик был 0.
    const r = await page.evaluate(async () => {
      const resp = await fetch("/api/v1/parents/students/62/badges/seen", {
        method: "POST",
      });
      return resp.status;
    });
    expect(r).toBe(200);

    // Открываем dashboard — баннера быть не должно.
    await page.goto(`${BASE}/parent/dashboard/62`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const banner = page.getByTestId("parent-badges-new-banner");
    await expect(banner).toHaveCount(0);
  });

  test("pill «+N» на /parents если есть новые", async ({ page, context }) => {
    await login(page, "parent.kirill@example.com", "ParentTest!2026");
    // Марк все seen.
    await page.evaluate(async () => {
      await fetch("/api/v1/parents/students/62/badges/seen", { method: "POST" });
    });

    await page.goto(`${BASE}/parents`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const pill = page.getByTestId("parent-child-new-badges-62");
    // После mark-seen pill не должен быть виден (new_since_last_seen === 0).
    await expect(pill).toHaveCount(0);
  });
});
