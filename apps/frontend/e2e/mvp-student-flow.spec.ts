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
    expectNoRawAiGarbage(await page.locator("main").innerText());
  });
});
