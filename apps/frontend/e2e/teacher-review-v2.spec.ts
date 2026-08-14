import { expect, test } from "@playwright/test";

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

test.describe("Teacher review mode V2", () => {
  test("shows route metadata and filters without raw JSON", async ({ page }) => {
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: 8, email: "teacher@example.com", display_name: "Teacher", role: "teacher" }),
      });
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
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(filtered) });
    });

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
});
