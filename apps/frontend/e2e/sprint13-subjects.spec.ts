import { test, expect } from "@playwright/test";

test("Sprint 13 search filters subjects", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL(/subjects/);

  // Должен быть search input
  const searchInput = page.locator('input#subject-search');
  await expect(searchInput).toBeVisible();

  // Найти «математика»
  await searchInput.fill("матем");
  await page.waitForTimeout(200);

  // Только математика visible
  const subjectCards = page.locator("a[href^='/subjects/']");
  const count = await subjectCards.count();
  expect(count).toBeGreaterThan(0);
  expect(count).toBeLessThan(12);

  // Все карточки содержат "матем" в name
  const allText = await subjectCards.allTextContents();
  for (const text of allText) {
    expect(text.toLowerCase()).toContain("матем");
  }
});

test("Sprint 13 search empty state", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL(/subjects/);

  const searchInput = page.locator('input#subject-search');
  await searchInput.fill("xyz_nonexistent_subject_12345");

  // EmptyState появляется
  await expect(page.getByText(/Ничего не найдено/i)).toBeVisible({
    timeout: 5_000,
  });
});

test("Sprint 13 search respects a11y (input has accessible label)", async ({
  page,
}) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL(/subjects/);

  const searchInput = page.locator('input#subject-search');
  // input ID связывается с label через for/id (a11y)
  const labelText = await page
    .locator('label[for="subject-search"]')
    .first()
    .textContent();
  expect(labelText).toContain("Поиск");
});
