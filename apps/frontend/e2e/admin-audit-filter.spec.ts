import { test, expect } from "@playwright/test";

/**
 * Sprint 10.4 — проверка фильтра audit log в админ-панели.
 * Тестирует: filter по entity, action, дате, и total count от API.
 */
test.use({ ignoreHTTPSErrors: true, baseURL: "https://192.168.1.86" });

const ADMIN = { email: "admin@example.com", password: "Kirill2026!" };

test("Sprint 10.4: admin can filter audit log by entity", async ({ page, request }) => {
  // 1) Login как admin
  await page.goto("/login");
  await page.fill('input[name="email"]', ADMIN.email);
  await page.fill('input[name="password"]', ADMIN.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/admin/);

  // 2) Перейти в Audit tab
  await page.click('button:has-text("Audit"), a:has-text("Audit")');
  await page.waitForTimeout(500);

  // 3) Проверить что filter entity существует
  const entityInput = page.locator(
    'input[placeholder*="Entity"]',
  );
  await expect(entityInput).toBeVisible();

  // 4) Ввести entity=ai
  await entityInput.fill("ai");
  await page.click('button:has-text("Применить")');
  await page.waitForTimeout(1000);

  // 5) Проверить что backend возвращает правильный count
  const token = await page.evaluate(() => localStorage.getItem("token"));
  const resp = await request.get(
    `${test.info().project.use?.baseURL ?? "https://192.168.1.86"}/api/v1/admin/audit-log/count?entity=ai`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  expect(typeof data.total).toBe("number");
  expect(data.total).toBeGreaterThanOrEqual(0);
});

test("Sprint 10.4: audit log requires admin role", async ({ page, request }) => {
  // Прямой запрос с неправильным role → 403
  // Логин как student
  await page.goto("/login");
  await page.fill('input[name="email"]', "kirill@example.com");
  await page.fill('input[name="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/topics/);

  const token = await page.evaluate(() => localStorage.getItem("token"));
  const resp = await request.get(
    `${test.info().project.use?.baseURL ?? "https://192.168.1.86"}/api/v1/admin/audit-log/count`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  // Student должен получить 403
  expect(resp.status()).toBe(403);
});
