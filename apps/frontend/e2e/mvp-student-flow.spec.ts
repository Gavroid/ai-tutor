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
  const averageMatch = question.match(/(?:числа|оценки)[^:]*:\s*([0-9,\.\s]+)\./i);
  if (averageMatch) {
    const nums = averageMatch[1]
      .split(/[,\s]+/)
      .map((x) => Number(x.replace(",", ".")))
      .filter((x) => Number.isFinite(x));
    if (nums.length > 0) {
      const avg = nums.reduce((a, b) => a + b, 0) / nums.length;
      return String(avg).replace(".", ",");
    }
  }
  const averageNumbers = [...question.matchAll(/-?\d+(?:[,.]\d+)?(?=\s*(?:°C|°|,|\.))/g)]
    .map((m) => Number(m[0].replace(",", ".")))
    .filter((x) => Number.isFinite(x));
  if (/средн/i.test(question) && averageNumbers.length >= 2) {
    const avg = averageNumbers.reduce((a, b) => a + b, 0) / averageNumbers.length;
    return String(avg).replace(".", ",");
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
    await page.waitForTimeout(8_000);
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
      await page.getByRole("button", { name: wrongOption }).click();
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
});
