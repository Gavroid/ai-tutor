import { expect, test } from "@playwright/test";

const dashboardPayload = {
  student: { id: 101, display_name: "Кирилл", email: "kid@example.com" },
  generated_at: "2026-08-14T15:00:00Z",
  total_attempts: 18,
  correct_attempts: 13,
  accuracy: 0.72,
  average_mastery: 0.64,
  subject_mastery: [
    {
      subject_id: 3,
      subject_name: "Математика (6 класс — повторение)",
      topics_total: 42,
      topics_attempted: 9,
      avg_mastery: 0.64,
      accuracy: 0.72,
    },
  ],
  weak_topics: [
    {
      topic_id: 195,
      topic_name: "Общий знаменатель",
      subject_name: "Математика",
      mastery: 0.42,
      attempts_count: 4,
    },
  ],
  top_mistakes: [],
  streak: {
    current_streak_days: 2,
    longest_streak_days: 5,
    last_active_date: "2026-08-14",
    total_active_days: 7,
  },
  time_stats: {
    total_attempts: 18,
    last_7_days: 6,
    last_30_days: 18,
    avg_per_active_day: 2.57,
  },
  daily_activity_30d: Array.from({ length: 30 }, (_, index) => ({
    date: `2026-08-${String(Math.max(1, index + 1)).padStart(2, "0")}`,
    attempts: index > 23 ? 1 : 0,
  })),
  due_for_review_count: 2,
  summary: "Есть темы для повторения: начните с «Общий знаменатель».",
  recommendations: [
    {
      title: "Повторить слабую тему",
      detail: "Начните с темы «Общий знаменатель»: mastery 42%, попыток 4.",
      tone: "warning",
      topic_id: 195,
      topic_name: "Общий знаменатель",
    },
  ],
  last_activity_label: "2026-08-14",
  privacy_note: "Родитель видит агрегированные метрики. Содержимое чатов ребёнка с AI-репетитором не отображается (приватность).",
};

test.describe("Parent dashboard V2", () => {
  test("shows actionable parent report cards without raw chat", async ({ page }) => {
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: 7, email: "parent@example.com", display_name: "Parent", role: "parent" }),
      });
    });
    await page.route("**/api/v1/parents/students/101/dashboard", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(dashboardPayload) });
    });

    await page.goto("/parent/dashboard/101");

    await expect(page.getByText("Что улучшилось")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Где нужна помощь")).toBeVisible();
    await expect(page.getByText("Что сделать завтра", { exact: true })).toBeVisible();
    await expect(page.getByText("Маршрут")).toBeVisible();
    await expect(page.getByText(/9\/42 тем/).first()).toBeVisible();
    await expect(page.getByText(/Общий знаменатель/).first()).toBeVisible();
    await expect(page.getByText(/Содержимое чатов ребёнка/)).toBeVisible();

    const mainText = await page.locator("main").innerText();
    expect(mainText).not.toMatch(/raw chat|chat message|user:|assistant:/i);
    expect(mainText).not.toContain("correct_answer");
  });
});
