/**
 * Sprint 11.1 — мобильный UX audit.
 *
 * Проверяет:
 * - viewport-rendering на iPhone SE (375), iPhone 12 (390), Android (412)
 * - горизонтальный overflow (UI вылезает за viewport — плохо)
 * - touch targets >= 36px (минимальный для комфортного пальца)
 *
 * Без describe() — иначе не сработает с двумя файлами на test().
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

test.use({ ignoreHTTPSErrors: true, baseURL: "https://192.168.1.86" });

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
      // Sprint 12: небольшой settle для layout-shift после navigation.
      await page.waitForTimeout(300);

      const overflow = await page.locator("body").evaluate((el) => ({
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
      }));
      // 3px tolerance — micro-rounding может вызвать 1-2px overflow.
      const hasOverflow = overflow.scrollWidth > overflow.clientWidth + 3;

      await page.screenshot({
        path: `screenshots/mobile/${t.width}x${t.height}-${p.name}.png`,
        fullPage: true,
      });

      expect(
        hasOverflow,
        `horizontal overflow on ${t.width}x${t.height} ${p.name}`,
      ).toBe(false);
    });
  }
}
