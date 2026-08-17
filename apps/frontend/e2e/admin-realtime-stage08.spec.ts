import { expect, test } from "@playwright/test";

const adminUser = {
  id: 1,
  email: "admin@example.com",
  display_name: "Admin",
  role: "admin",
  is_active: true,
};

const realtimeSnapshot = {
  ts: "2026-08-17T12:30:00Z",
  ai_modes: { explain: { ok: 3, error: 0 } },
  ai_tokens: { input: 1200, output: 800 },
  http_total: { "2xx": 44, "4xx": 2, "5xx": 0 },
  http_breakdown: [
    { path: "/api/v1/student/topics/{topic_id}/draft", status: "404", count: 2, bucket: "4xx", kind: "expected", reason: "missing_topic_draft" },
  ],
  system: {
    db: "ok",
    redis: "ok",
    backend: "ok",
    upload_disk_used_percent: 46.9,
    backup_latest_age_seconds: 180,
    mem_used_pct: null,
    mem_used_mb: 596.3,
    mem_limit_mb: null,
  },
};

test.describe("Admin realtime Stage 08", () => {
  test("shows operator DB Redis backup and disk signals without SSH", async ({ page }) => {
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(adminUser) });
    });
    await page.route("**/api/v1/admin/audit-log**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    });
    await page.route("**/api/v1/admin/realtime/snapshot", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(realtimeSnapshot) });
    });

    await page.goto("/admin?tab=realtime");

    await expect(page.getByText("Real-time метрики")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("DB", { exact: true })).toBeVisible();
    await expect(page.getByText("Redis", { exact: true })).toBeVisible();
    await expect(page.getByText("Backup age", { exact: true })).toBeVisible();
    await expect(page.getByText("Upload disk", { exact: true })).toBeVisible();
    await expect(page.getByText("App-level SELECT 1 probe from backend /metrics")).toBeVisible();
    await expect(page.getByText("Latest visible backup manifest age; critical above 26h")).toBeVisible();
    await expect(page.getByText("Warning threshold: 80% used")).toBeVisible();
    await expect(page.getByText("0", { exact: true }).first()).toBeVisible();
  });
});
