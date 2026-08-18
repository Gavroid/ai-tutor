import { expect, test, type Page } from "@playwright/test";

const PARENT = {
  email: "parent-e2e@example.com",
  password: "Kirill2026!",
};

async function loginAsParent(page: Page): Promise<void> {
  await page.goto("/login");
  await page.locator("input[type='email']").first().fill(PARENT.email);
  await page.locator("input[type='password']").first().fill(PARENT.password);
  await page.getByRole("button", { name: /войти|вход|логин/i }).first().click();
  await page.waitForLoadState("networkidle", { timeout: 15_000 });
}

function expectNoRawChildData(text: string): void {
  expect(text).not.toMatch(/question_text|user_answer|correct_answer|feedback|history|messages/i);
  expect(text).not.toMatch(/RAW_PRIVATE|OTHER_PRIVATE/i);
  expect(text).not.toContain('"correct_answer"');
}

test.describe("Stage 23 parent privacy", () => {
  test("parent dashboard stays aggregate-only and role boundaries hold", async ({ page }) => {
    test.setTimeout(90_000);
    await loginAsParent(page);

    const childrenResponse = await page.request.get("/api/v1/parents/children");
    expect(childrenResponse.status()).toBe(200);
    const children = (await childrenResponse.json()) as Array<{ student_id: number }>;
    expect(children.length).toBeGreaterThan(0);
    const linkedStudentId = children[0].student_id;

    const dashboardResponse = await page.request.get(`/api/v1/parents/students/${linkedStudentId}/dashboard`);
    expect(dashboardResponse.status()).toBe(200);
    const dashboard = await dashboardResponse.json();
    const dashboardText = JSON.stringify(dashboard);
    expect(dashboard.privacy_note).toMatch(/чат|приват/i);
    expect(dashboard.total_attempts).toBeDefined();
    expect(dashboard.subject_mastery).toBeDefined();
    expect(dashboard.weak_topics).toBeDefined();
    expect(dashboard.top_mistakes).toBeDefined();
    expectNoRawChildData(dashboardText);

    const unrelatedResponse = await page.request.get("/api/v1/parents/students/99999/dashboard");
    expect(unrelatedResponse.status()).toBe(404);
    expectNoRawChildData(await unrelatedResponse.text());

    for (const path of [
      "/api/v1/teacher/topics/readiness",
      "/api/v1/teacher/materials",
      "/api/v1/admin/audit-log",
      "/api/v1/admin/realtime/snapshot",
      "/api/v1/admin/users",
    ]) {
      const response = await page.request.get(path);
      expect(response.status(), `${path} should be forbidden for parent`).toBe(403);
    }

    await page.goto("/parents");
    await expect(page.getByText(/Родительский|Parent Console/i).first()).toBeVisible({ timeout: 15_000 });
    const visibleText = await page.locator("body").innerText();
    expect(visibleText).toMatch(/переписка.*приват|агрегированные метрики|приват/i);
    expectNoRawChildData(visibleText);
  });
});
