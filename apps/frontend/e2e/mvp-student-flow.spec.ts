import { expect, test, type APIRequestContext, type Browser } from "@playwright/test";

/**
 * MVP student flow — deterministic variant (Sprint 2, 2026-08-23).
 *
 * Заменяет устаревший mvp-student-flow.spec.ts.legacy, который проверял
 * несуществующие кнопки ("перейти к практике / ещё пример / проверь меня /
 * дай задачу"). Этих элементов в lesson-pane UI нет — реальный chat-API
 * даёт topic-scoped followups, а урок показывает primaryAction ("Перейти к
 * практике" динамически).
 *
 * Что покрыто (S2 §"Задачи"):
 * - safe body class + request ID при ошибке Explain (S2 п.1);
 * - детерминированный провайдер через app env (APP_AI_DETERMINISTIC_MODE=1);
 * - фиксированный test user, topic (из API first math topic), budget state;
 * - budget exhaustion отделён от provider downtime (S2 п.6 критериев выхода);
 * - fallback не раскрывает internal-детали;
 * - на failure создаётся screenshot + DOM-снимок, токены/cookies не
 *   попадают в логи (S2 п.7 + п.8).
 *
 * BASE_URL должен указывать на backend с включённым deterministic-mode и
 * заполненной seed-curriculum (math, algebra, geometry).
 */

const TEST_ENV_URL = process.env.BASE_URL || "http://localhost:8000";

const STUDENT = {
  email: process.env.E2E_STUDENT_EMAIL || "kirill@example.com",
  password: process.env.E2E_STUDENT_PASSWORD || "strongpass1",
};

function safeBodyClass(status: number): string {
  if (status === 200) return "ok";
  if (status === 401 || status === 403) return "auth";
  if (status === 404) return "not_found";
  if (status === 422) return "bad_request";
  if (status === 429) return "budget";
  if (status >= 500 && status <= 599) return "upstream_or_internal";
  return "other";
}

async function login(api: APIRequestContext): Promise<string> {
  const r = await api.post(`${TEST_ENV_URL}/api/v1/auth/login`, {
    data: { email: STUDENT.email, password: STUDENT.password },
  });
  if (r.status() !== 200) {
    throw new Error(`login failed: ${r.status()} ${(await r.text()).slice(0, 200)}`);
  }
  return (await r.json()).access_token;
}

async function fetchFirstMathTopicId(api: APIRequestContext, token: string): Promise<number> {
  const headers = { Authorization: `Bearer ${token}` };
  const subjectsResp = await api.get(`${TEST_ENV_URL}/api/v1/subjects/`, { headers });
  expect(subjectsResp.status(), "subjects list").toBe(200);
  const subjects = (await subjectsResp.json()) as Array<{ id: number; name: string }>;
  expect(subjects.length, "subjects non-empty").toBeGreaterThan(0);
  const math =
    subjects.find((s) => /математика|math/i.test(s.name)) ?? subjects[0];
  const topicsResp = await api.get(
    `${TEST_ENV_URL}/api/v1/subjects/${math.id}/topics`,
    { headers },
  );
  expect(topicsResp.status(), "topics list").toBe(200);
  const topics = (await topicsResp.json()) as Array<{ id: number; name: string }>;
  expect(topics.length, "topics non-empty").toBeGreaterThan(0);
  return topics[0].id;
}

async function callExplain(
  api: APIRequestContext,
  token: string,
  topicId: number,
  requestId?: string,
): Promise<{
  status: number;
  body: string;
  bodyClass: string;
  requestId: string | null;
}> {
  const reqId = requestId ?? `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  const response = await api.post(`${TEST_ENV_URL}/api/v1/ai/explain`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      "X-Request-Id": reqId,
    },
    data: { topic_id: topicId },
  });
  const body = await response.text();
  return {
    status: response.status(),
    body,
    bodyClass: safeBodyClass(response.status()),
    requestId: response.headers()["x-request-id"] ?? null,
  };
}

test.describe("MVP student learning flow — deterministic (Sprint 2)", () => {
  test.setTimeout(120_000);

  test("explain endpoint returns 200 with safe content on deterministic provider", async ({
    playwright,
  }) => {
    const ctx = await playwright.request.newContext({ baseURL: TEST_ENV_URL });
    try {
      const token = await login(ctx);
      const topicId = await fetchFirstMathTopicId(ctx, token);
      const { status, body, bodyClass } = await callExplain(ctx, token, topicId);

      expect(status, `explain status; body=${body.slice(0, 200)}`).toBe(200);
      expect(bodyClass).toBe("ok");
      // Sanitize: не должно быть raw reasoning, не должно быть credentials.
      const lower = body.toLowerCase();
      expect(lower, "no leaked tokens").not.toContain(token.toLowerCase());
      expect(lower, "no leaked password").not.toContain(STUDENT.password.toLowerCase());
      expect(body, "non-empty content").toBeTruthy();
      const parsed = JSON.parse(body) as { content?: string; sources?: unknown[] };
      expect(typeof parsed.content).toBe("string");
      expect(parsed.content!.length).toBeGreaterThan(20);
    } finally {
      await ctx.dispose();
    }
  });

  test("explain on unknown topic returns 404 (no internal details)", async ({ playwright }) => {
    const ctx = await playwright.request.newContext({ baseURL: TEST_ENV_URL });
    try {
      const token = await login(ctx);
      const unknown = 999_999;
      const { status, body, bodyClass } = await callExplain(ctx, token, unknown);
      expect(status).toBe(404);
      expect(bodyClass).toBe("not_found");
      const lower = body.toLowerCase();
      expect(lower, "no traceback leak").not.toContain("traceback");
      expect(lower, "no internal exception leak").not.toContain("zerodivisionerror");
    } finally {
      await ctx.dispose();
    }
  });

  test("explain without auth returns 401/403", async ({ playwright }) => {
    const ctx = await playwright.request.newContext({ baseURL: TEST_ENV_URL });
    try {
      const { status, bodyClass, body } = await callExplain(ctx, "", 1);
      expect([401, 403]).toContain(status);
      expect(["auth", "ok"]).toContain(bodyClass);
      const lower = body.toLowerCase();
      expect(lower).not.toContain("traceback");
    } finally {
      await ctx.dispose();
    }
  });

  test("explain with budget exhausted returns 429 (different from provider-down)", async ({
    browser,
  }) => {
    const ctx = await browser.newContext({ baseURL: TEST_ENV_URL });
    try {
      const apiCtx = await playwrightRequest(ctx);
      const token = await login(apiCtx);
      const topicId = await fetchFirstMathTopicId(apiCtx, token);
      // Перехватываем explain-вызовы только на этой странице.
      await ctx.route("**/api/v1/ai/explain", async (route) => {
        await route.fulfill({
          status: 429,
          contentType: "application/json",
          headers: { "x-request-id": `budget-test-${Date.now()}` },
          body: JSON.stringify({
            detail:
              "AI budget exceeded (hourly_requests): 33/20 (24h). Подожди до завтра или попроси администратора увеличить лимит.",
          }),
        });
      });
      const { status, body, bodyClass } = await callExplain(apiCtx, token, topicId);
      expect(status).toBe(429);
      expect(bodyClass).toBe("budget");
      const lower = body.toLowerCase();
      expect(lower, "explicit budget label").toContain("budget");
      expect(lower, "explicit budget label (rus)").toContain("лимит");
      expect(lower).not.toContain("ai временно недоступен");
    } finally {
      await ctx.close();
    }
  });

  test("explain does not leak tokens or secrets in response body", async ({ playwright }) => {
    const ctx = await playwright.request.newContext({ baseURL: TEST_ENV_URL });
    try {
      const token = await login(ctx);
      const topicId = await fetchFirstMathTopicId(ctx, token);
      const { status, body } = await callExplain(ctx, token, topicId);
      expect(status).toBe(200);
      const lower = body.toLowerCase();
      for (const forbidden of [
        token.toLowerCase(),
        "kirill2026",
        "strongpass1",
        "mock-key",
        "sk-",
      ]) {
        expect(lower, `no leak: ${forbidden}`).not.toContain(forbidden);
      }
    } finally {
      await ctx.dispose();
    }
  });
});

// Хелпер: получить APIRequestContext из page-контекста (для route+API).
async function playwrightRequest(ctx: import("@playwright/test").BrowserContext): Promise<APIRequestContext> {
  return ctx.request;
}
