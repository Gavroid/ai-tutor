import { expect, test, type Page, type APIRequestContext } from "@playwright/test";

type Credentials = { email: string; password: string };

const USERS = {
  student: { email: "kirill@example.com", password: "Kirill2026!" },
  parent: { email: "parent-e2e@example.com", password: "Kirill2026!" },
  teacher: { email: "teacher@example.com", password: "Kirill2026!" },
  admin: { email: "admin@example.com", password: "Kirill2026!" },
} as const;

async function login(page: Page, who: Credentials): Promise<void> {
  await page.goto("/login");
  await page.locator("input[type='email']").first().fill(who.email);
  await page.locator("input[type='password']").first().fill(who.password);
  await page.getByRole("button", { name: /войти|вход|логин/i }).first().click();
  await page.waitForLoadState("networkidle", { timeout: 15_000 });
}

async function expectForbidden(request: APIRequestContext, paths: string[]): Promise<void> {
  for (const path of paths) {
    const response = await request.get(path);
    expect(response.status(), `${path} should be forbidden`).toBe(403);
  }
}

test.describe("Stage 24 teacher/admin RBAC", () => {
  test("student and parent cannot access teacher/admin surfaces", async ({ browser }) => {
    test.setTimeout(90_000);
    const forbiddenTeacher = [
      "/api/v1/teacher/topics/readiness",
      "/api/v1/teacher/materials",
      "/api/v1/teacher/rag/jobs/not-found",
    ];
    const forbiddenAdmin = [
      "/api/v1/admin/audit-log",
      "/api/v1/admin/audit-log/count",
      "/api/v1/admin/users",
      "/api/v1/admin/stats",
      "/api/v1/admin/ops/status",
      "/api/v1/admin/realtime/snapshot",
    ];

    for (const who of [USERS.student, USERS.parent]) {
      const context = await browser.newContext();
      const page = await context.newPage();
      await login(page, who);
      await expectForbidden(context.request, [...forbiddenTeacher, ...forbiddenAdmin]);
      await context.close();
    }
  });

  test("teacher can access teacher surface but not admin surface", async ({ page }) => {
    await login(page, USERS.teacher);

    const readiness = await page.request.get("/api/v1/teacher/topics/readiness");
    expect(readiness.status()).toBe(200);
    const materials = await page.request.get("/api/v1/teacher/materials");
    expect(materials.status()).toBe(200);

    await expectForbidden(page.request, [
      "/api/v1/admin/audit-log",
      "/api/v1/admin/users",
      "/api/v1/admin/stats",
      "/api/v1/admin/realtime/snapshot",
    ]);
  });

  test("admin can access audit and realtime endpoints", async ({ page }) => {
    await login(page, USERS.admin);

    for (const path of [
      "/api/v1/admin/audit-log",
      "/api/v1/admin/users",
      "/api/v1/admin/stats",
      "/api/v1/admin/realtime/snapshot",
    ]) {
      const response = await page.request.get(path);
      expect(response.status(), `${path} should be admin-accessible`).toBe(200);
    }
  });
});
