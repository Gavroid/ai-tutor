import { test, expect } from "@playwright/test";

test("Sprint 14 Tab order on login (form works without mouse)", async ({
  page,
}) => {
  await page.goto("/login");
  // Tab → focus Email
  await page.locator("body").press("Tab");
  // First focusable — skip-link or email input
  const tag = await page.evaluate(() => document.activeElement?.tagName);
  expect(["A", "INPUT"]).toContain(tag);
});

test("Sprint 14 Enter submits login form", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "kirill@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.press('input[type="password"]', "Enter");
  // Должны уйти с /login (Sprint 11.1 redirect).
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), {
    timeout: 15_000,
  });
});

test("Sprint 14 AddStudentModal traps focus and Escape closes", async ({
  page,
}) => {
  // Login как admin сначала
  await page.goto("/login");
  await page.fill('input[type="email"]', "admin@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  // Sprint 11.1: после login admin → /admin. Но URL matching дефолт waitForLoadState
  // 'load' иногда не срабатывает — используем функцию.
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), {
    timeout: 15_000,
  });
  if (!page.url().includes("/admin")) {
    await page.goto("/admin");
  }
  await page.waitForLoadState("domcontentloaded");

  // Sprint 7.1: data-testid="add-student-button" используется в admin page.
  const addBtn = page.locator('[data-testid="add-student-button"]');
  await expect(addBtn, "AddStudent button should be visible").toBeVisible({
    timeout: 5_000,
  });
  await addBtn.click();

  // Sprint 14: модалка должна иметь role=dialog + aria-modal=true.
  const dialog = page.locator('[role="dialog"][aria-modal="true"]');
  await expect(dialog).toBeVisible({ timeout: 3_000 });

  // Escape должен закрывать.
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden({ timeout: 3_000 });
});

test("Sprint 14 AddStudentModal Tab cycles within modal", async ({
  page,
}) => {
  await page.goto("/login");
  await page.fill('input[type="email"]', "admin@example.com");
  await page.fill('input[type="password"]', "Kirill2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), {
    timeout: 15_000,
  });
  if (!page.url().includes("/admin")) {
    await page.goto("/admin");
  }
  await page.waitForLoadState("domcontentloaded");

  const addBtn = page.locator('[data-testid="add-student-button"]');
  await expect(addBtn).toBeVisible({ timeout: 5_000 });
  await addBtn.click();

  const dialog = page.locator('[role="dialog"][aria-modal="true"]');
  await expect(dialog).toBeVisible();

  // Tab несколько раз — focus не должен покидать диалог.
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press("Tab");
    const inDialog = await page.evaluate(() => {
      const dialog = document.querySelector('[role="dialog"][aria-modal="true"]');
      return dialog ? dialog.contains(document.activeElement) : false;
    });
    expect(inDialog, `Tab #${i} should keep focus in dialog`).toBe(true);
  }
});
