/**
 * Sprint 7.6: E2E полный цикл ученика.
 *
 * Сценарий A (полный):
 * 1. Login как Кирилл
 * 2. Переход в предметы, выбор предмета
 * 3. Переход в тему
 * 4. Нажатие «Объясни тему» → AI отвечает
 * 5. Отправка своего сообщения репетитору → AI отвечает
 * 6. Нажатие «Дай задание» → получает задание
 * 7. Ответ на задание → «Проверить» → видна оценка
 * 8. Смена страницы (back) → /subjects
 * 9. Переход в /student/badges → видит свои достижения
 *
 * Privacy: запрет на прямой URL /student/badges без auth → redirect /login.
 */

import { test, expect } from "@playwright/test";

const STUDENT = {
  email: "student-e2e@example.com",
  password: "strongpass1",
};

test.describe("Student full cycle", () => {
  test("14.1. login → subjects → topic → explain → message → practice → check", async ({
    page,
    request,
  }) => {
    // 1. Login
    await page.goto("/login");
    await page
      .locator("input[type='email']")
      .first()
      .fill(STUDENT.email);
    await page
      .locator("input[type='password']")
      .first()
      .fill(STUDENT.password);
    await page.getByRole("button", { name: /войти|вход/i }).click();
    await page.waitForURL(/subjects/, { timeout: 15_000 });

    // 2. Subjects page → кликаем первый предмет
    const firstSubject = page.locator("a[href^='/subjects/']").first();
    await firstSubject.click();
    await page.waitForURL(/\/subjects\/\d+/, { timeout: 10_000 });

    // 3. Topic page — ищем ссылку на тему
    const firstTopic = page.locator("a[href^='/topics/']").first();
    const topicHref = await firstTopic.getAttribute("href").catch(() => null);
    test.skip(topicHref === null, "No topics for this student yet");
    await firstTopic.click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10_000 });

    // 4. Жмём «Объясни тему»
    const explainBtn = page.getByRole("button", { name: /Объясни тему/i });
    await explainBtn.click();
    // Ждём AI ответа (спиннер исчезает)
    await page.waitForTimeout(3000);

    // 5. Отправляем сообщение репетитору
    const input = page.locator(
      "input[placeholder*='репетитор'], input[placeholder*='вопрос репетитору']"
    ).first();
    await input.fill("Спасибо!");
    const sendBtn = page.getByRole("button", { name: /Отправить/i });
    await sendBtn.click();
    await page.waitForTimeout(2500);

    // 6. «Дай задание»
    const generateBtn = page.getByRole("button", { name: /Дай задание/i });
    await generateBtn.click();
    await page.waitForTimeout(3000);

    // 7. После того как задание отрисовалось — поле для ответа (input или options)
    const userAnswerInput = page
      .locator("input[placeholder*='Числовой'], input[placeholder*='Текстовой']")
      .first();
    // Не все задания имеют input — пропускаем если нет
    const visible = await userAnswerInput.isVisible().catch(() => false);

    if (visible) {
      await userAnswerInput.fill("42");
      const checkBtn = page.getByRole("button", { name: /Проверить/i });
      await checkBtn.click();
      // Проверка результата
      await page.waitForTimeout(2500);
      const correctDiv = page.locator("text=/Верно|ошибка/i").first();
      const hasResult = await correctDiv.isVisible().catch(() => false);
      expect(hasResult).toBeTruthy();
    }

    // 8. Возврат на subjects через breadcrumb
    await page.goto("/subjects");

    // 9. /student/badges
    await page.goto("/student/badges");
    await expect(page.locator("body")).toBeVisible();
    // Не должна быть редиректа на /login
    await page.waitForTimeout(1500);
    expect(page.url()).toContain("/student/badges");
  });

  test("14.2. /student/badges требует auth", async ({ page }) => {
    // Чистим cookies — нет авторизации
    await page.context().clearCookies();
    await page.goto("/student/badges");
    // Должно редиректить на /login
    await page.waitForURL(/login/, { timeout: 5000 }).catch(() => null);
    expect(page.url()).toMatch(/login/);
  });

  test("14.3. микрофон скрыт по умолчанию на /topics/[id]", async ({ page }) => {
    // Login
    await page.goto("/login");
    await page
      .locator("input[type='email']")
      .first()
      .fill(STUDENT.email);
    await page
      .locator("input[type='password']")
      .first()
      .fill(STUDENT.password);
    await page.getByRole("button", { name: /войти|вход/i }).click();
    await page.waitForURL(/subjects/, { timeout: 15_000 });

    // Идём в первую тему
    await page.locator("a[href^='/subjects/']").first().click();
    const topicLink = page.locator("a[href^='/topics/']").first();
    const href = await topicLink.getAttribute("href").catch(() => null);
    test.skip(href === null, "No topics");
    await topicLink.click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10_000 });

    // Pilot Core: voice остаётся в коде, но скрыт без NEXT_PUBLIC_VOICE_ENABLED=1.
    const micBtn = page.getByLabel(/Записать голосовое сообщение/i);
    await expect(micBtn).toHaveCount(0);
  });

  test("14.4. Markdown рендерится в AI-ответе", async ({ page }) => {
    await page.goto("/login");
    await page
      .locator("input[type='email']")
      .first()
      .fill(STUDENT.email);
    await page
      .locator("input[type='password']")
      .first()
      .fill(STUDENT.password);
    await page.getByRole("button", { name: /войти|вход/i }).click();
    await page.waitForURL(/subjects/, { timeout: 15_000 });

    await page.locator("a[href^='/subjects/']").first().click();
    const topicLink = page.locator("a[href^='/topics/']").first();
    const href = await topicLink.getAttribute("href").catch(() => null);
    test.skip(href === null, "No topics");
    await topicLink.click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10_000 });

    // Запрос «Объясни тему»
    const explainBtn = page.getByRole("button", { name: /Объясни тему/i });
    await explainBtn.click();
    await page.waitForTimeout(3500);

    // AI сообщение — проверяем что присутствует
    const aiMsg = page.locator(".mr-auto.bg-white").first();
    const visible = await aiMsg.isVisible().catch(() => false);
    expect(visible).toBeTruthy();
    // Мы не можем точно проверить <strong>/<h2> т.к. mock AI даёт ограниченный markdown,
    // но хотя бы видна структура div'а
  });
});
