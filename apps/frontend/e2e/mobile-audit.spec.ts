import { test, expect, devices } from "@playwright/test";

/**
 * Sprint 11.1 — мобильный UX audit.
 * Запускает ключевые страницы на iPhone (375x667) и Android (412x915).
 * Проверяет: viewport-rendering, overflow, кнопки доступные для пальца.
 */

const TARGETS = [
  { name: "iPhone SE (375x667)", width: 375, height: 667 },
  { name: "iPhone 12 (390x844)", width: 390, height: 844 },
  { name: "Android (412x915)", width: 412, height: 915 },
];

const PAGES = [
  { name: "login", url: "/login", login: false },
  { name: "subjects (after login)", url: "/subjects", login: true },
  { name: "topic detail", url: "/topics/31", login: true },
  { name: "student badges", url: "/student/badges", login: true },
  { name: "parents (parent role)", url: "/parents", login: "parent" },
];

test.describe("Mobile UX audit", () => {
  test.use({ ignoreHTTPSErrors: true, baseURL: "https://192.168.1.86" });

  for (const t of TARGETS) {
    for (const p of PAGES) {
      test(`${t.name}: ${p.name}`, async ({ page }) => {
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

        // Detect горизонтальный overflow (UI вылезает за viewport — bad UX)
        const body = page.locator("body");
        const overflow = await body.evaluate((el) => ({
          scrollWidth: el.scrollWidth,
          clientWidth: el.clientWidth,
        }));
        const hasOverflow = overflow.scrollWidth > overflow.clientWidth + 5;

        await page.screenshot({
          path: `screenshots/mobile/${t.width}x${t.height}-${p.name.replace(/\s/g, "_")}.png`,
          fullPage: true,
        });

        // Touch-target sizing: проверка что кнопки / input >= 44px (Apple HIG).
        const smallTargets = await page.evaluate(() => {
          const interactive = document.querySelectorAll(
            'button, a[href], input, select, textarea',
          );
          const problems: { tag: string; size: number; text: string }[] = [];
          for (const el of Array.from(interactive).slice(0, 30)) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            const min = Math.min(rect.width, rect.height);
            if (min < 36) {
              problems.push({
                tag: el.tagName,
                size: Math.round(min),
                text: (el.textContent || "").trim().slice(0, 30),
              });
            }
          }
          return problems;
        });

        // Report (без вала чтобы было видно всё)
        console.log(
          `[${t.width}x${t.height}] ${p.name}:`,
          `overflow=${hasOverflow ? "YES" : "no"}`,
          `smallTargets=${smallTargets.length}`,
        );
        // Soft assert — UX bug log для дальнейшего фикса
        if (hasOverflow) {
          console.warn(
            `[WARNING] Horizontal overflow on ${t.width}x${t.height} ${p.name}`,
          );
        }
      });
    }
  }
});
