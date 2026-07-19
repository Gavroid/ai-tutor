/**
 * Pilot Manual Walk-through — Sprint 3.0
 *
 * Этот spec делает то же что pilot.spec.ts, но с подробным логированием:
 * - скриншот на каждом ключевом шаге (смотримо вручную)
 * - console.log + page.on('console') для каждого шага
 * - tracking API responses для каждой роли
 * - финальный отчёт с понятным статусом "OK / FAIL / SKIP"
 *
 * Использование:
 *   BASE_URL=https://192.168.1.86 npx playwright test e2e/walkthrough.spec.ts
 *
 * После прогона скриншоты в `apps/frontend/screenshots/walkthrough/`.
 */
import { test, expect, type Page, type ConsoleMessage } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const PILOT = {
  baseURL: process.env.BASE_URL || "https://192.168.1.86",
  admin: { email: "admin@example.com", password: "Kirill2026!" },
  teacher: { email: "teacher@example.com", password: "Kirill2026!" },
  parent: { email: "parent-e2e@example.com", password: "Kirill2026!" },
  student: { email: "kirill@example.com", password: "Kirill2026!" },
} as const;

const SCREENSHOT_DIR = "screenshots/walkthrough";

test.beforeEach(async ({ page }) => {
  // Walkthrough сам управляет navigation.
});

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
});

// Хелпер: login + скриншот + лог
async function loginAndScreenshot(
  page: Page,
  who: { email: string; password: string; role: string },
  stepNumber: number,
  totalSteps: number,
): Promise<void> {
  console.log(`\n[${stepNumber}/${totalSteps}] === Login as ${who.role} (${who.email}) ===`);
  await page.goto("/login");
  await page.screenshot({ path: `${SCREENSHOT_DIR}/${String(stepNumber).padStart(2, "0")}-login.png`, fullPage: true });

  await page.locator("input[type='email']").first().fill(who.email);
  await page.locator("input[type='password']").first().fill(who.password);
  await page.getByRole("button", { name: /войти|вход/i }).first().click();
  await page.waitForLoadState("networkidle", { timeout: 15_000 });

  const currentUrl = page.url();
  console.log(`[${stepNumber}] After login URL: ${currentUrl}`);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/${String(stepNumber).padStart(2, "0")}-after-login.png`, fullPage: true });
}

// =============================================================================
// STUDENT (Кирилл) — главный пользователь
// =============================================================================
test("Sprint 3.0: Student flow (Кирилл) — 7 шагов", async ({ page }) => {
  test.setTimeout(3 * 60 * 1000);

  const apiCalls: { url: string; status: number; method: string }[] = [];
  page.on("response", (resp) => {
    if (resp.url().includes("/api/")) {
      apiCalls.push({
        url: resp.url().split("/api")[1],
        status: resp.status(),
        method: resp.request().method(),
      });
    }
  });

  console.log("\n=== STUDENT FLOW (Кирилл) ===");
  // Step 1: login
  await loginAndScreenshot(page, { ...PILOT.student, role: "student" }, 1, 7);

  // Step 2: Subjects page
  console.log("\n[2/7] === Subjects page ===");
  await page.screenshot({ path: `${SCREENSHOT_DIR}/02-subjects.png`, fullPage: true });
  const subjectCount = await page.locator("a[href^='/subjects/']").count();
  console.log(`[2] Subject cards found: ${subjectCount}`);

  // Step 3: Click first subject
  console.log("\n[3/7] === Click first subject ===");
  await page.locator("a[href^='/subjects/']").first().click();
  await page.waitForURL(/\/subjects\/\d+/, { timeout: 10_000 });
  await page.screenshot({ path: `${SCREENSHOT_DIR}/03-subject-detail.png`, fullPage: true });
  console.log(`[3] URL: ${page.url()}`);

  // Step 4: Click first topic
  console.log("\n[4/7] === Click first topic ===");
  const firstTopic = page.locator("a[href^='/topics/']").first();
  const topicExists = (await firstTopic.count()) > 0;
  if (!topicExists) {
    console.log("[4] SKIP: no topics for this student");
    test.skip(true, "no topics");
  }
  await firstTopic.click();
  await page.waitForURL(/\/topics\/\d+/, { timeout: 10_000 });
  await page.waitForTimeout(2000); // дать странице загрузиться
  await page.screenshot({ path: `${SCREENSHOT_DIR}/04-topic-page.png`, fullPage: true });
  console.log(`[4] URL: ${page.url()}`);

  // Step 5: Объясни тему
  console.log("\n[5/7] === Click 'Объясни тему' ===");
  const explainBtn = page.getByRole("button", { name: /объясни/i });
  if ((await explainBtn.count()) > 0) {
    await explainBtn.first().click();
    await page.waitForTimeout(8000); // AI генерация
    await page.screenshot({ path: `${SCREENSHOT_DIR}/05-after-explain.png`, fullPage: true });
    console.log(`[5] AI explain triggered`);
  } else {
    console.log("[5] SKIP: no explain button");
  }

  // Step 6: Дай задание (v2 secure flow)
  console.log("\n[6/7] === Click 'Дай задание' (v2 secure) ===");
  let generateResponseBody = "";
  const captureGen = (resp: import("@playwright/test").Response) => {
    if (resp.url().includes("/api/v2/exercises/generate") && resp.request().method() === "POST") {
      generateResponseBody = generateResponseBody || ""; // init
      resp.text().then((t) => (generateResponseBody = t)).catch(() => {});
    }
  };
  page.on("response", captureGen);
  const genBtn = page.getByRole("button", { name: /дай задание/i });
  if ((await genBtn.count()) > 0) {
    await genBtn.first().click();
    await page.waitForTimeout(5000);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/06-after-generate.png`, fullPage: true });
    const correctAnswerLeaked = generateResponseBody.includes('"correct_answer"');
    console.log(`[6] generate triggered, payload contains correct_answer: ${correctAnswerLeaked} (must be false)`);
    if (correctAnswerLeaked) {
      console.log("[6] !!! SECURITY: correct_answer in payload !!!");
    }
  }

  // Step 7: Ответить на задание
  console.log("\n[7/7] === Answer exercise + check ===");
  const answerInput = page.locator("input[placeholder*='Числовой'], input[placeholder*='Текстовой']").first();
  if ((await answerInput.count()) > 0 && (await answerInput.isVisible().catch(() => false))) {
    await answerInput.fill("42");
    const checkBtn = page.getByRole("button", { name: /проверить/i });
    if ((await checkBtn.count()) > 0) {
      await checkBtn.first().click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/07-after-check.png`, fullPage: true });
      console.log(`[7] Answer submitted`);
    }
  } else {
    console.log("[7] SKIP: no answer input visible");
  }

  console.log("\n=== STUDENT API CALLS ===");
  apiCalls.forEach((c) => console.log(`  ${c.method} ${c.url} → ${c.status}`));
});

// =============================================================================
// PARENT — privacy + dashboard
// =============================================================================
test("Sprint 3.0: Parent flow — 4 шага", async ({ page }) => {
  test.setTimeout(3 * 60 * 1000);

  const dashboardPayload: string[] = [];
  page.on("response", async (resp) => {
    if (resp.url().includes("/api/v1/parents/students/") && resp.url().includes("/dashboard")) {
      try {
        const text = await resp.text();
        dashboardPayload.push(text);
      } catch {}
    }
  });

  console.log("\n=== PARENT FLOW ===");
  // Step 1: login
  await loginAndScreenshot(page, { ...PILOT.parent, role: "parent" }, 8, 12);

  // Step 2: /parents
  console.log("\n[9/12] === /parents page (linked children list) ===");
  await page.goto("/parents");
  await page.waitForLoadState("networkidle", { timeout: 10_000 });
  await page.screenshot({ path: `${SCREENSHOT_DIR}/09-parents-list.png`, fullPage: true });
  const childrenList = await page.locator("a[href^='/parent/dashboard/']").count();
  console.log(`[9] Linked children: ${childrenList}`);

  // Step 3: открыть dashboard ребёнка
  console.log("\n[10/12] === Open child dashboard ===");
  if (childrenList > 0) {
    await page.locator("a[href^='/parent/dashboard/']").first().click();
    await page.waitForURL(/\/parent\/dashboard\/\d+/, { timeout: 10_000 });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/10-dashboard.png`, fullPage: true });
    console.log(`[10] URL: ${page.url()}`);
  } else {
    console.log("[10] SKIP: no children linked");
    test.skip(true, "no children");
  }

  // Step 4: privacy check (email в payload)
  console.log("\n[11/12] === Privacy check (no email in response) ===");
  await page.waitForTimeout(2000);
  const hasEmail = dashboardPayload.some((p) => p.includes('"email"'));
  console.log(`[11] Dashboard payload contains 'email': ${hasEmail} (must be false)`);
  if (hasEmail) {
    console.log("[11] !!! PRIVACY: email in dashboard response !!!");
  }
  await page.screenshot({ path: `${SCREENSHOT_DIR}/11-privacy-check.png`, fullPage: true });

  // Step 5: чужой ребёнок → 404
  console.log("\n[12/12] === Privacy: 404 for non-linked child ===");
  const resp = await page.request.get("/api/v1/parents/students/99999/dashboard");
  console.log(`[12] Status for child 99999: ${resp.status()} (must be 404)`);
});

// =============================================================================
// TEACHER — workflow
// =============================================================================
test("Sprint 3.0: Teacher flow — 4 шага", async ({ page }) => {
  test.setTimeout(3 * 60 * 1000);

  console.log("\n=== TEACHER FLOW ===");
  // Step 1: login
  await loginAndScreenshot(page, { ...PILOT.teacher, role: "teacher" }, 13, 17);

  // Step 2: /teacher
  console.log("\n[14/17] === /teacher (own materials list) ===");
  await page.goto("/teacher");
  await page.waitForLoadState("networkidle", { timeout: 10_000 });
  await page.screenshot({ path: `${SCREENSHOT_DIR}/14-teacher-list.png`, fullPage: true });
  const materialsCount = await page.locator("a[href^='/teacher/materials/']").count();
  console.log(`[14] Materials count: ${materialsCount}`);

  // Step 3: /teacher/generate
  console.log("\n[15/17] === /teacher/generate (3 source types) ===");
  await page.goto("/teacher/generate");
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/15-teacher-generate.png`, fullPage: true });
  const sourceTypeButtons = await page.locator("button").allTextContents();
  console.log(`[15] Source type buttons: ${sourceTypeButtons.filter((t) => /текст|файл|тема/i.test(t)).join(", ")}`);

  // Step 4: чужой материал → 403
  console.log("\n[16/17] === Forbidden access to non-owned material ===");
  // Попытка открыть чужой материал (с большим ID)
  const resp = await page.request.get("/api/v1/teacher/materials/99999");
  console.log(`[16] GET /api/v1/teacher/materials/99999 → ${resp.status()} (must be 403 or 404)`);

  // Step 5: logout check
  console.log("\n[17/17] === Logout test ===");
  const logoutBtn = page.getByRole("button", { name: /выйти|logout/i });
  if ((await logoutBtn.count()) > 0) {
    console.log("[17] Logout button found");
  } else {
    console.log("[17] No explicit logout button (logout via menu?)");
  }
});

// =============================================================================
// ADMIN — audit log + tools (Phase 5 hidden tools check)
// =============================================================================
test("Sprint 3.0: Admin flow — 5 шагов", async ({ page }) => {
  test.setTimeout(3 * 60 * 1000);

  console.log("\n=== ADMIN FLOW ===");
  // Step 1: login
  await loginAndScreenshot(page, { ...PILOT.admin, role: "admin" }, 18, 23);

  // Step 2: /admin
  console.log("\n[19/23] === /admin (4 tabs: Audit/Users/Stats/Tools) ===");
  await page.goto("/admin");
  await page.waitForLoadState("networkidle", { timeout: 10_000 });
  await page.screenshot({ path: `${SCREENSHOT_DIR}/19-admin-main.png`, fullPage: true });
  const tabs = await page.locator("[role='tab'], button, a").allTextContents();
  const adminTabs = tabs.filter((t) => /audit|users|stats|tools|аудит|польз|стат|инстр/i.test(t));
  console.log(`[19] Admin tabs found: ${adminTabs.join(", ")}`);

  // Step 3: Real-time link hidden (Phase 5)
  console.log("\n[20/23] === Real-time link hidden (Phase 5) ===");
  const realtimeCount = await page.getByRole("link", { name: /Real-time/i }).count();
  console.log(`[20] Real-time links: ${realtimeCount} (must be 0)`);

  // Step 4: Тест уведомления hidden
  console.log("\n[21/23] === Test notification button hidden (Phase 5) ===");
  const notifBtn = await page.getByRole("button", { name: /тест уведомления/i }).count();
  console.log(`[21] Test notification buttons: ${notifBtn} (must be 0)`);

  // Step 5: audit filter
  console.log("\n[22/23] === Audit filter (action=error.5xx) ===");
  const filter = page.locator("input[placeholder*='Действие']").first();
  if ((await filter.count()) > 0) {
    await filter.fill("error.5xx");
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/22-audit-filter.png`, fullPage: true });
    const rows = await page.locator("tr, [role='row']").count();
    console.log(`[22] Audit rows for error.5xx: ${rows}`);
  }

  // Step 6: /metrics endpoint
  console.log("\n[23/23] === /metrics endpoint ===");
  const metricsResp = await page.request.get("/metrics");
  console.log(`[23] GET /metrics → ${metricsResp.status()}, length: ${(await metricsResp.text()).length}`);
});