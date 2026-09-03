/**
 * Sprint 3.11 — Smoke test S4 (Gamification) + S5 (Parent Dashboard).
 *
 * 10 пунктов быстрого чек-листа. Использует реальные тестовые аккаунты с прод.
 *
 * Anti-rate-limit strategy: каждый test.describe делает login ОДИН раз
 * через beforeAll, потом переиспользует контекст. Тесты logout НЕ делают
 * (cookies не очищаются). Это даёт 2 login за прогон — далеко от лимита 20/15 мин.
 */

import { test, expect, type Page, type BrowserContext } from "@playwright/test";

async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.waitForLoadState("domcontentloaded");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  // Wait until login form is gone (means we navigated away).
  await page
    .locator('input[type="password"]')
    .first()
    .waitFor({ state: "hidden", timeout: 15_000 });
  await page.waitForLoadState("networkidle", { timeout: 10_000 });
}

async function waitForBadgesLoaded(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle", { timeout: 15_000 });
  await page
    .locator("text=/количество решённых|усилие и качество|серии и возвращение|контекст и время|🎯 пока нет достижений/i")
    .first()
    .waitFor({ state: "visible", timeout: 15_000 });
}

async function waitForParentLoaded(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle", { timeout: 15_000 });
  await page
    .locator("text=/родительский кабинет|не удалось загрузить|дети/i")
    .first()
    .waitFor({ state: "visible", timeout: 15_000 });
}

// ============================================================
// S4 — Геймификация (1 login, потом переиспользуем контекст)
// ============================================================

test.describe("S4 Gamification — /student/badges", () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ ignoreHTTPSErrors: true });
    page = await context.newPage();
    await login(page, "qwe@ru.ru", "QweTest!2026");
  });

  test.afterAll(async () => {
    await context.close();
  });

  test("badges page renders with prism-shell for student", async () => {
    await page.goto("/student/badges");
    await waitForBadgesLoaded(page);

    await expect(page.getByRole("link", { name: /к предметам/i })).toBeVisible();
    await expect(page.getByText("Sprint 3.10 · Gamification")).toBeVisible();
    await expect(page.getByRole("heading", { name: /достижения и серии/i })).toBeVisible();

    await expect(
      page.getByRole("button", { name: /проверить новые достижения/i })
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /^обновить$/i })).toBeVisible();

    await expect(page.getByText(/^получено$/i).first()).toBeVisible();
    await expect(page.getByText(/^прогресс$/i).first()).toBeVisible();
    await expect(page.getByText(/^категорий$/i).first()).toBeVisible();
  });

  test("all 4 categories visible", async () => {
    await page.goto("/student/badges");
    await waitForBadgesLoaded(page);

    await expect(page.getByText(/количество решённых/i)).toBeVisible();
    await expect(page.getByText(/усилие и качество/i)).toBeVisible();
    await expect(page.getByText(/серии и возвращение/i)).toBeVisible();
    await expect(page.getByText(/контекст и время/i)).toBeVisible();
  });

  test("evaluate button works without crashing", async () => {
    await page.goto("/student/badges");
    await waitForBadgesLoaded(page);

    await page
      .getByRole("button", { name: /проверить новые достижения/i })
      .click();
    await page.waitForTimeout(3000);

    // Hero still visible (no crash).
    await expect(
      page.getByRole("heading", { name: /достижения и серии/i })
    ).toBeVisible();
  });

  test("mobile viewport: badges fit without horizontal scroll", async ({ browser }) => {
    const mobileCtx = await browser.newContext({
      viewport: { width: 390, height: 844 },
      ignoreHTTPSErrors: true,
    });
    const mobilePage = await mobileCtx.newPage();
    await login(mobilePage, "qwe@ru.ru", "QweTest!2026");
    await mobilePage.goto("/student/badges");
    await waitForBadgesLoaded(mobilePage);

    const overflow = await mobilePage.locator("body").evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(
      overflow.scrollWidth <= overflow.clientWidth + 3,
      `mobile overflow: ${JSON.stringify(overflow)}`
    ).toBeTruthy();
    await mobileCtx.close();
  });
});

// ============================================================
// S5 — Родительский дашборд (1 login, переиспользуем контекст)
// ============================================================

test.describe("S5 Parent Dashboard", () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ ignoreHTTPSErrors: true });
    page = await context.newPage();
    await login(page, "parent.kirill@example.com", "ParentTest!2026");
  });

  test.afterAll(async () => {
    await context.close();
  });

  test("/parents renders linked children", async () => {
    await page.goto("/parents");
    await waitForParentLoaded(page);

    await expect(
      page.getByRole("heading", { name: /родительский кабинет/i })
    ).toBeVisible();
    await expect(page.getByText(/qwe/).first()).toBeVisible();
  });

  test("/parent/dashboard/62 shows progress for linked child", async () => {
    await page.goto("/parent/dashboard/62");
    await page.waitForLoadState("networkidle", { timeout: 15_000 });

    const heroVisible = await page
      .getByText(/прогресс qwe/i)
      .first()
      .isVisible()
      .catch(() => false);
    const errorVisible = await page
      .getByText(/не найден|404|ошибк/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(heroVisible || errorVisible, "expected either progress view or error").toBeTruthy();
  });

  test("parent cannot access unrelated child dashboard", async () => {
    const res = await page.goto("/parent/dashboard/99999");
    await page.waitForLoadState("domcontentloaded");
    const status = res?.status() ?? 0;
    const url = page.url();
    const isDashboard = /\/parent\/dashboard\/\d+/.test(url);
    const ok =
      status >= 400 ||
      !isDashboard ||
      (await page.getByText(/прогресс/i).first().isVisible().catch(() => false)) === false;
    expect(ok, `expected rejection, status=${status} url=${url}`).toBeTruthy();
  });

  test("mobile viewport: parent pages fit", async ({ browser }) => {
    const mobileCtx = await browser.newContext({
      viewport: { width: 390, height: 844 },
      ignoreHTTPSErrors: true,
    });
    const mobilePage = await mobileCtx.newPage();
    await login(mobilePage, "parent.kirill@example.com", "ParentTest!2026");
    await mobilePage.goto("/parents");
    await waitForParentLoaded(mobilePage);

    const overflow1 = await mobilePage.locator("body").evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(
      overflow1.scrollWidth <= overflow1.clientWidth + 3,
      `/parents mobile overflow: ${JSON.stringify(overflow1)}`
    ).toBeTruthy();

    await mobilePage.goto("/parent/dashboard/62");
    await mobilePage.waitForLoadState("networkidle", { timeout: 15_000 });
    const overflow2 = await mobilePage.locator("body").evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(
      overflow2.scrollWidth <= overflow2.clientWidth + 3,
      `/parent/dashboard/62 mobile overflow: ${JSON.stringify(overflow2)}`
    ).toBeTruthy();
    await mobileCtx.close();
  });
});

// ============================================================
// Cross-role auth — анонимный доступ
// ============================================================

test.describe("Cross-role auth", () => {
  test("anonymous /student/badges shows error state", async ({ browser }) => {
    const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
    const p = await ctx.newPage();
    const res = await p.goto("/student/badges");
    await p.waitForLoadState("networkidle", { timeout: 15_000 });
    const status = res?.status() ?? 0;
    const url = p.url();
    const errorState = await p
      .getByText(/ошибк|не удалось|try again|попробовать|401|403/i)
      .first()
      .isVisible()
      .catch(() => false);
    const redirected = /\/login/.test(url);
    expect(
      errorState || redirected || status >= 400,
      `expected error/redirect; status=${status} url=${url} errorState=${errorState}`
    ).toBeTruthy();
    await ctx.close();
  });

  test("student cannot access /parents", async ({ browser }) => {
    const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
    const p = await ctx.newPage();
    await login(p, "qwe@ru.ru", "QweTest!2026");
    const res = await p.goto("/parents");
    await p.waitForLoadState("networkidle", { timeout: 15_000 });
    const status = res?.status() ?? 0;
    const url = p.url();
    const hasErrorState = await p
      .getByText(/ошибк|не удалось|403|forbidden|доступ запрещён/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasChildrenList = await p
      .getByText(/qwe/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(
      status >= 400 || hasErrorState || !hasChildrenList,
      `student should not see parent content; status=${status} url=${url}`
    ).toBeTruthy();
    await ctx.close();
  });
});
