/**
 * Sprint 11.1 - mobile UX audit.
 */
import { test, expect } from "@playwright/test";

const TARGETS = [
  { name: "iPhone_SE", width: 375, height: 667 },
  { name: "iPhone_12", width: 390, height: 844 },
  { name: "Android", width: 412, height: 915 },
];

const PAGES = [
  { name: "login", url: "/login", login: false },
  { name: "subjects", url: "/subjects", login: "student" },
  { name: "topic_detail", url: "/topics/31", login: "student" },
  { name: "badges", url: "/student/badges", login: "student" },
  { name: "parents", url: "/parents", login: "parent" },
];

for (const t of TARGETS) {
  for (const p of PAGES) {
    test(`mobile_${t.name}_${p.name}`, async ({ page }) => {
      await page.setViewportSize({ width: t.width, height: t.height });

      if (p.login) {
        const email =
          p.login === "parent" ? "parent-e2e@example.com" : "kirill@example.com";
        await page.goto("/login");
        await page.fill('input[type="email"]', email);
        await page.fill('input[type="password"]', "Kirill2026!");
        await page.click('button[type="submit"]');
        await page.waitForLoadState("networkidle", { timeout: 15_000 });
      }

      await page.goto(p.url);
      await page.waitForLoadState("networkidle", { timeout: 15_000 });
      await page.waitForTimeout(300);

      const overflow = await page.locator("body").evaluate((el) => ({
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
      }));
      const hasOverflow = overflow.scrollWidth > overflow.clientWidth + 3;

      expect(
        hasOverflow,
        `overflow on ${t.width}x${t.height} ${p.name}`,
      ).toBe(false);
    });
  }
}
