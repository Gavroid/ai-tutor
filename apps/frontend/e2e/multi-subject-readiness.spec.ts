import { expect, test, type Page } from "@playwright/test";

const STUDENT = {
  email: "kirill@example.com",
  password: "Kirill2026!",
};

async function loginAsStudent(page: Page): Promise<void> {
  await page.goto("/login");
  await page.locator("input[type='email'], input[name='email']").first().fill(STUDENT.email);
  await page.locator("input[type='password']").first().fill(STUDENT.password);
  await page.getByRole("button", { name: /войти|вход|логин/i }).click();
  await page.waitForURL(/\/subjects/, { timeout: 15_000 });
}

test.describe("Stage 7 multi-subject readiness (pilot_visible filter)", () => {
  test("student sees only pilot-visible subjects (math)", async ({ page }) => {
    await loginAsStudent(page);
    await page.goto("/subjects");
    await expect(page.getByText("Каталог предметов")).toBeVisible({ timeout: 10_000 });

    // Только math должна быть видна ребёнку.
    const cards = page.locator("a[href^='/subjects/']");
    await expect(cards).toHaveCount(1, { timeout: 10_000 });

    const mathCard = cards.first();
    await expect(mathCard).toContainText(/Математика .*повторение/i);
    await expect(mathCard.getByText("MVP-ready")).toHaveCount(2);
    await expect(mathCard).toContainText(/объяснения, практика/i);
  });

  test("student gets locked screen on non-pilot subject URL", async ({ page }) => {
    await loginAsStudent(page);

    // Прямой переход на algebra должна показать "Subject locked" экран.
    await page.goto("/subjects/4"); // algebra id=4
    await expect(page.getByText(/Subject locked/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/проходит evidence-проверку/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /В каталог предметов/i })).toBeVisible();
  });

  test("math subject page shows readiness panel and topics for student", async ({ page }) => {
    await loginAsStudent(page);
    await page.goto("/subjects/3"); // math id=3
    await expect(page.getByText("Readiness Panel")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("MVP-ready.")).toBeVisible();
    await expect(page.getByText("RAG")).toBeVisible();
    await expect(page.getByText("ON").first()).toBeVisible();
    await expect(page.getByText("Маршрут тем")).toBeVisible();
  });
});
