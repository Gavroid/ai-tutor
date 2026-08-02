import { expect, test } from "@playwright/test";

const STUDENT = {
  email: "kirill@example.com",
  password: "Kirill2026!",
};

async function loginAsStudent(page: import("@playwright/test").Page): Promise<void> {
  await page.goto("/login");
  await page.locator("input[type='email'], input[name='email']").first().fill(STUDENT.email);
  await page.locator("input[type='password']").first().fill(STUDENT.password);
  await page.getByRole("button", { name: /войти|вход|логин/i }).click();
  await page.waitForURL(/\/subjects/, { timeout: 15_000 });
}

function expectNoRawAiGarbage(text: string): void {
  expect(text.toLowerCase()).not.toContain("<think");
  expect(text.toLowerCase()).not.toContain("&lt;think");
  expect(text).not.toContain("{&quot;");
  expect(text).not.toMatch(/```json/i);
  expect(text).not.toContain("&amp;gt;");
  expect(text).not.toContain("&gt;");
  expect(text).not.toContain("$$");
  expect(text).not.toContain("\\\\frac");
  expect(text).not.toContain("\\\\text");
  expect(text).not.toMatch(/\|\s*-{3,}\s*\|/);
  expect(text).not.toMatch(/"correct_answer"\s*:/);
}

function answerForMvpQuestion(question: string, options: string[] | null): string {
  if (options?.includes("7") && question.includes("8") && question.includes("9") && question.includes("4")) return "7";
  if (options?.includes("30") && question.includes("20%")) return "30";
  if (options?.includes("20") && question.includes("x/5")) return "20";
  if (options?.includes("4") && question.includes("2x + 3 = 11")) return "4";
  if (options?.includes("0,24") && question.includes("0,6") && question.includes("0,4")) return "0,24";

  const fractions = [...question.matchAll(/(\d+)\s*\/\s*(\d+)/g)].map((m) => ({
    n: Number(m[1]),
    d: Number(m[2]),
  }));
  if (fractions.length >= 2 && fractions[0].d === fractions[1].d) {
    return `${fractions[0].n + fractions[1].n}/${fractions[0].d}`;
  }
  const averageMatch = question.match(/(?:числа|чисел|оценки|значения)[^:]*:\s*([0-9,\.\sи-]+)\./i);
  if (averageMatch) {
    const nums = [...averageMatch[1].matchAll(/-?\d+(?:[,.]\d+)?/g)]
      .map((m) => Number(m[0].replace(",", ".")))
      .filter((x) => Number.isFinite(x));
    if (nums.length > 0) {
      const avg = nums.reduce((a, b) => a + b, 0) / nums.length;
      return String(avg).replace(".", ",");
    }
  }
  const allNumbers = [...question.matchAll(/-?\d+(?:[,.]\d+)?/g)]
    .map((m) => Number(m[0].replace(",", ".")))
    .filter((x) => Number.isFinite(x));
  if (/средн/i.test(question) && allNumbers.length >= 2) {
    const avg = allNumbers.reduce((a, b) => a + b, 0) / allNumbers.length;
    const base = String(avg).replace(".", ",");
    const optionWithUnit = options?.find((opt) => opt.replace(/[^0-9,.-]/g, "") === base);
    return optionWithUnit ?? base;
  }
  if (question.includes("1/2") && question.includes("1/3")) return "5/6";
  if (options && options.length > 0) return options[0];
  throw new Error(`Cannot infer answer for generated MVP question: ${question}`);
}

test.describe("MVP student learning flow", () => {
  test("student can open topic, request explain, generate practice, and see clean feedback", async ({
    page,
  }) => {
    test.setTimeout(90_000);

    await loginAsStudent(page);

    await page.goto("/subjects/3");
    await page.waitForURL(/\/subjects\/3/, { timeout: 10_000 });

    const firstTopic = page.locator("a[href^='/topics/']").first();
    await expect(firstTopic).toBeVisible({ timeout: 10_000 });
    await firstTopic.click();
    await page.waitForURL(/\/topics\/\d+/, { timeout: 10_000 });

    await page.getByRole("button", { name: /объяснить|объясни тему/i }).click();
    await expect(page.locator("text=AI думает")).toBeVisible({ timeout: 5_000 }).catch(() => undefined);
    await expect(page.getByRole("button", { name: /практика|дай задание/i })).toBeEnabled({ timeout: 45_000 });
    await expect(page.getByRole("button", { name: /среднее чисел/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: /средняя скорость/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /средний вес/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /копировать/i })).toHaveCount(0);
    expectNoRawAiGarbage(await page.locator("main").innerText());

    const generateResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v2/exercises/generate") &&
        response.request().method() === "POST",
      { timeout: 30_000 },
    );
    await page.getByRole("button", { name: /практика|дай задание/i }).click();
    const generateResponse = await generateResponsePromise;
    const generateBody = await generateResponse.text();
    expect(generateResponse.ok()).toBeTruthy();
    expect(generateBody).not.toContain("correct_answer");
    expectNoRawAiGarbage(generateBody);

    await expect(page.getByText(/Задание/i).first()).toBeVisible({ timeout: 10_000 });
    const mainAfterGenerate = await page.locator("main").innerText();
    expectNoRawAiGarbage(mainAfterGenerate);

    const parsedGenerate = JSON.parse(generateBody) as { question_text: string; options: string[] | null };
    const questionText = parsedGenerate.question_text;
    const answer = answerForMvpQuestion(questionText, parsedGenerate.options);
    const wrongOption = parsedGenerate.options?.find((opt) => opt !== answer);
    if (wrongOption) {
      await page.getByRole("button", { name: wrongOption, exact: true }).click();
      const wrongResponsePromise = page.waitForResponse(
        (response) => response.url().includes("/api/v2/exercises/") && response.url().includes("/answer"),
        { timeout: 30_000 },
      );
      await page.getByRole("button", { name: /проверить/i }).click();
      const wrongResponse = await wrongResponsePromise;
      expect(wrongResponse.ok()).toBeTruthy();
      const wrongBody = await wrongResponse.json();
      expect(wrongBody.is_correct).toBeFalsy();
      await expect(page.getByText("Есть ошибка").first()).toBeVisible({ timeout: 10_000 });
    }

    if (parsedGenerate.options?.includes(answer)) {
      await page.getByRole("button", { name: answer }).click();
      await expect(page.getByText("Есть ошибка")).toHaveCount(0);
    } else {
      await page.locator("input[placeholder='Числовой ответ'], input[placeholder='Текстовый ответ']").first().fill(answer);
      await expect(page.getByText("Есть ошибка")).toHaveCount(0);
    }
    const answerResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/api/v2/exercises/") && response.url().includes("/answer"),
      { timeout: 30_000 },
    );
    await page.getByRole("button", { name: /проверить/i }).click();
    const answerResponse = await answerResponsePromise;
    expect(answerResponse.ok()).toBeTruthy();
    const answerBody = await answerResponse.json();
    expect(answerBody.is_correct).toBeTruthy();
    await expect(page.getByText("Верно!").first()).toBeVisible({ timeout: 10_000 });

    await page.locator("input[placeholder='Задай вопрос репетитору…']").fill("Объясни проще про дроби");
    await page.getByRole("button", { name: /отправить/i }).click();
    await expect(page.getByText("Объясни проще про дроби")).toBeVisible({ timeout: 5_000 });
    await expect(page.locator("main").getByText("AI временно недоступен")).toHaveCount(0, { timeout: 20_000 });
    await expect(page.locator("main").getByText("WS закрыт")).toHaveCount(0, { timeout: 20_000 });
    await expect(page.getByTestId("chat-message-assistant").last()).toBeVisible({ timeout: 20_000 });
    expectNoRawAiGarbage(await page.locator("main").innerText());

    await page.getByRole("button", { name: /очистить/i }).click();
    await page.getByRole("button", { name: /да, удалить/i }).click();
    await expect(page.getByTestId("exercise-card")).toHaveCount(0);
    await expect(page.getByText("Верно!")).toHaveCount(0);
    await expect(page.getByText("Объясни проще про дроби")).toHaveCount(0);
    await expect(page.locator("input[placeholder='Задай вопрос репетитору…']")).toHaveValue("");
  });

  test("student sees clear AI budget message instead of provider-down text", async ({ page }) => {
    await loginAsStudent(page);
    await page.goto("/topics/187");
    await page.waitForURL(/\/topics\/187/, { timeout: 10_000 });

    await page.route("**/api/v1/ai/explain", async (route) => {
      await route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "AI budget exceeded (hourly_requests): 33/20 (24h). Подожди до завтра или попроси администратора увеличить лимит.",
        }),
      });
    });

    await page.getByRole("button", { name: /объяснить|объясни тему/i }).click();

    await expect(page.getByText(/лимит|много запросов|подожди/i).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("main").getByText("AI временно недоступен")).toHaveCount(0);
  });
});
