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

test.describe("Stage 7 multi-subject readiness", () => {
  test("subjects clearly separate MVP-ready math from preview subjects", async ({ page }) => {
    await loginAsStudent(page);

    await page.goto("/subjects");
    await expect(page.getByText("Каталог предметов")).toBeVisible({ timeout: 10_000 });

    const mathCard = page
      .locator("a[href^='/subjects/']")
      .filter({ hasText: /Математика .*повторение/i })
      .first();
    await expect(mathCard).toBeVisible({ timeout: 10_000 });
    await expect(mathCard.getByText("MVP-ready")).toHaveCount(2);
    await expect(mathCard).toContainText(/объяснения, практика/i);

    const previewCard = page
      .locator("a[href^='/subjects/']")
      .filter({ hasText: /Алгебра/i })
      .first();
    await expect(previewCard).toBeVisible({ timeout: 10_000 });
    await expect(previewCard.getByText("Preview")).toHaveCount(2);
    await expect(previewCard).toContainText(/материалы\/RAG ещё не подтверждены/i);

    await mathCard.click();
    await page.waitForURL(/\/subjects\/\d+/, { timeout: 10_000 });
    await expect(page.getByText("Readiness Panel")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("MVP-ready.")).toBeVisible();
    await expect(page.getByText("RAG")).toBeVisible();
    await expect(page.getByText("ON").first()).toBeVisible();
    await expect(page.getByText("Practice")).toBeVisible();

    await page.goto("/subjects");
    const previewHref = await previewCard.getAttribute("href");
    expect(previewHref).toBeTruthy();
    await page.goto(previewHref!);
    await expect(page.getByText("Readiness Panel")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Preview-предмет.")).toBeVisible();
    await expect(page.getByText(/материалы\/RAG ещё не подтверждены/i)).toBeVisible();
    await expect(page.getByText("OFF").first()).toBeVisible();
  });
});
