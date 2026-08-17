import { expect, test, type Route } from "@playwright/test";

const analytics = {
  totals: { attempts: 18, correct: 13, accuracy: 0.72, active_topics: 2, weak_topics: 1, average_mastery: 0.64 },
  subjects: [
    { subject_id: 3, subject_code: "math", subject_name: "Математика", attempts: 18, correct: 13, accuracy: 0.72, average_mastery: 0.64, active_topics: 2, weak_topics: 1 },
  ],
  weak_topics: [
    { topic_id: 187, topic_name: "Среднее арифметическое", subject_id: 3, subject_code: "math", subject_name: "Математика", mastery_score: 0.42, attempts_count: 5, correct_count: 2 },
  ],
  recent_activity: [{ date: "2026-08-17", attempts: 4, correct: 3 }],
};

const rows = [
  {
    topic_id: 187,
    topic_name: "Среднее арифметическое",
    section_id: 10,
    section_name: "Вычисления и построения",
    subject_id: 3,
    subject_name: "Математика",
    priority: "P0",
    route_order: 1,
    route_tier: "base",
    route_focus: "средние значения",
    route_checkpoint: false,
    material_count: 1,
    chunk_count: 3,
    fallback_count: 3,
    followup_count: 3,
    explain_status: "Smoke OK",
    practice_status: "Smoke OK",
    source_status: "Verified",
    manual_qa_status: "Smoke OK",
  },
  {
    topic_id: 190,
    topic_name: "Виды треугольников",
    section_id: 10,
    section_name: "Вычисления и построения",
    subject_id: 3,
    subject_name: "Математика",
    priority: "P1",
    route_order: 4,
    route_tier: "base",
    route_focus: "виды треугольников",
    route_checkpoint: true,
    material_count: 1,
    chunk_count: 2,
    fallback_count: 1,
    followup_count: 3,
    explain_status: "Smoke OK",
    practice_status: "Smoke OK",
    source_status: "Verified",
    manual_qa_status: "TODO",
  },
] as const;

const topic = {
  id: 187,
  section_id: 10,
  name: "Среднее арифметическое",
  description: "Как находить среднее значение",
  difficulty: 1,
  order_index: 1,
};

const material = {
  id: 501,
  topic_id: 187,
  title: "Среднее арифметическое — QA smoke",
  status: "ai_generated",
  source_type: "topic",
  generated_by: 8,
  approved_by: null,
  published_at: null,
  created_at: "2026-08-17T12:00:00Z",
  content: {
    title: "Среднее арифметическое — QA smoke",
    purpose: "Понять, как находить среднее значение набора чисел.",
    connection_to_prior: null,
    key_ideas: [{ idea: "Сложить значения и разделить на их количество", terms: ["сумма", "количество"] }],
    rule_or_formula: "Среднее = сумма чисел / количество чисел",
    simple_example: "Для 2, 4, 6 среднее равно (2+4+6)/3 = 4.",
    schema_or_table: null,
    misconception: "Среднее не всегда равно одному из чисел набора.",
    common_mistake: "Забыть разделить сумму на количество чисел.",
    self_check_questions: ["Что нужно сделать первым?"],
    practice_tasks: [
      {
        difficulty: "easy",
        question_text: "Найди среднее чисел 2, 4, 6.",
        reference_solution: "(2 + 4 + 6) / 3 = 4",
        typical_mistakes: ["Разделить на 2 вместо 3"],
        hint: "Сначала сложи все числа.",
      },
    ],
    mini_test: [
      { question_text: "Что такое среднее?", options: ["Сумма / количество", "Только максимум"], correct_index: 0, explanation: "Среднее учитывает все значения." },
    ],
    flashcards: [{ question: "Формула среднего", answer: "Сумма / количество" }],
    ai_uncertainty_notes: ["Проверить формулировки перед публикацией"],
  },
} as const;

function fulfillJson(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

test.describe("Teacher review mode V2", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/auth/me", async (route) => {
      await fulfillJson(route, { id: 8, email: "teacher@example.com", display_name: "Teacher", role: "teacher" });
    });
    await page.route("**/api/v1/analytics/learning**", async (route) => fulfillJson(route, analytics));
    await page.route("**/api/v1/teacher/materials?**", async (route) => fulfillJson(route, [material]));
    await page.route("**/api/v1/teacher/materials", async (route) => fulfillJson(route, [material]));
    await page.route("**/api/v1/topics/187", async (route) => fulfillJson(route, topic));
    await page.route("**/api/v1/teacher/topics/187/followups", async (route) => {
      if (route.request().method() === "PUT") return fulfillJson(route, [{ label: "Дальше", prompt: "Продолжи", kind: "next", order_index: 1 }]);
      return fulfillJson(route, [{ label: "Дальше", prompt: "Продолжи", kind: "next", order_index: 1 }]);
    });
    await page.route("**/api/v1/teacher/topics/187/fallbacks", async (route) => {
      if (route.request().method() === "PUT") return fulfillJson(route, []);
      return fulfillJson(route, []);
    });
    await page.route("**/api/v1/teacher/topics/187/status", async (route) => fulfillJson(route, { ok: true, topic_id: 187, status: { manual_qa_status: "ok", notes: "Stage 07 smoke" } }));
    await page.route("**/api/v1/teacher/rag/rebuild-topic/187", async (route) => fulfillJson(route, { job_id: "rag-topic-187-smoke", topic_id: 187, subject_id: 3, status: "succeeded", chunks_before: 3, chunks_after: 3, message: "dry-run" }));
    await page.route("**/api/v1/teacher/materials/501", async (route) => fulfillJson(route, material));
    await page.route("**/api/v1/teacher/materials/501/quality-status", async (route) => {
      const payload = route.request().postDataJSON() as { status: string; note?: string };
      const status = payload.status === "approved" ? "teacher_approved" : payload.status;
      await fulfillJson(route, { ...material, status, approved_by: status === "teacher_approved" ? 8 : null });
    });
    await page.route("**/api/v1/teacher/topics/readiness**", async (route) => {
      const url = new URL(route.request().url());
      const checkpoint = url.searchParams.get("checkpoint");
      const routeTier = url.searchParams.get("route_tier");
      const filtered = rows.filter((row) => {
        if (routeTier && row.route_tier !== routeTier) return false;
        if (checkpoint === "true" && !row.route_checkpoint) return false;
        return true;
      });
      await fulfillJson(route, filtered);
    });
  });

  test("shows route metadata and filters without raw JSON", async ({ page }) => {
    await page.goto("/teacher/topics");

    await expect(page.getByText("Route tier")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Manual status")).toBeVisible();
    await expect(page.getByText("Checkpoints only")).toBeVisible();
    await expect(page.locator("table").getByText("1").first()).toBeVisible();
    await expect(page.locator("table").getByText("base").first()).toBeVisible();
    await expect(page.locator("table").getByText(/checkpoint/).first()).toBeVisible();
    await expect(page.locator("table").getByRole("link", { name: /Среднее арифметическое/ })).toBeVisible();

    await page.getByLabel("Route tier").selectOption("base");
    await page.getByLabel("Checkpoints only").check();
    await expect(page.locator("table").getByRole("link", { name: /Виды треугольников/ })).toBeVisible();

    const mainText = await page.locator("main").innerText();
    expect(mainText).not.toContain("{");
    expect(mainText).not.toContain("correct_answer");
  });

  test("runs analytics to readiness to topic detail to material QA without raw student chat", async ({ page }) => {
    await page.goto("/teacher");

    await expect(page.getByText("Learning Analytics")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Агрегаты по темам и предметам, без сырого AI-чата ученика.")).toBeVisible();
    await expect(page.getByText("Среднее арифметическое — QA smoke")).toBeVisible();
    await page.getByRole("link", { name: "Готовность тем" }).click();

    const readinessTable = page.locator("table");
    await expect(readinessTable.getByRole("link", { name: /Среднее арифметическое/ })).toBeVisible();
    await readinessTable.getByRole("link", { name: /Среднее арифметическое/ }).click();

    await expect(page.getByText("Готовность публикации")).toBeVisible();
    await expect(page.getByText("Manual QA статус")).toBeVisible();
    await page.goto("/teacher/materials/501");
    await expect(page.getByText("Content QA Workflow")).toBeVisible();
    await page.getByLabel("QA note").fill("Stage 07 needs-review smoke");
    await page.getByRole("button", { name: "Needs review" }).click();
    await expect(page.getByText("Нужна проверка")).toBeVisible();
    await expect(page.getByRole("button", { name: "🚀 Опубликовать" })).toHaveCount(0);

    await page.getByLabel("QA note").fill("Stage 07 blocked smoke");
    await page.getByRole("button", { name: "Blocked" }).click();
    await expect(page.getByText("Заблокировано")).toBeVisible();
    await expect(page.getByRole("button", { name: "🚀 Опубликовать" })).toHaveCount(0);

    const mainText = await page.locator("main").innerText();
    expect(mainText).not.toContain("raw AI chat");
    expect(mainText).not.toContain("correct_answer");
    expect(mainText).not.toContain("{");
  });
});
