import { expect, test, type Page } from "@playwright/test";

const PARENT = {
  email: "parent-e2e@example.com",
  password: "Kirill2026!",
} as const;

async function loginAsParent(page: Page): Promise<void> {
  await page.goto("/login");
  await page.locator("input[type='email']").first().fill(PARENT.email);
  await page.locator("input[type='password']").first().fill(PARENT.password);
  await page.getByRole("button", { name: /войти/i }).click();
  await page.waitForURL(/\/(parents|subjects)/, { timeout: 15_000 });
}

test.describe("Parent console", () => {
  test("parent console uses Prism UI and can create an invite", async ({ page }) => {
    await loginAsParent(page);
    await page.goto("/parents");
    await expect(page.getByText("Родительский кабинет")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Привязать ребёнка")).toBeVisible();

    const visual = await page.evaluate(() => ({
      prismShell: Boolean(document.querySelector(".prism-shell")),
      legacyWhiteClasses: Boolean(document.querySelector(".bg-white,.border-slate-200,.text-slate-600")),
      whitePanels: [...document.querySelectorAll("main *")].filter(
        (element) => getComputedStyle(element).backgroundColor === "rgb(255, 255, 255)",
      ).length,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    }));

    expect(visual.prismShell).toBe(true);
    expect(visual.legacyWhiteClasses).toBe(false);
    expect(visual.whitePanels).toBe(0);
    expect(visual.overflow).toBe(0);

    const inviteResponse = page.waitForResponse(
      (response) => response.url().includes("/api/v1/parents/invite") && response.request().method() === "POST",
      { timeout: 10_000 },
    );
    await page.getByRole("button", { name: /создать код/i }).click();
    const response = await inviteResponse;
    expect(response.ok()).toBe(true);
    await expect(page.getByText("Код для ребёнка", { exact: true })).toBeVisible({ timeout: 10_000 });
  });
});
