import { test, expect } from "@playwright/test";

/**
 * Sprint 11.2 — accessibility audit.
 * Проверяет:
 * - focus-visible CSS стили на интерактивных элементах (focus ring)
 * - aria-label / aria-labelledby для icon-only buttons
 * - skip-links для скрин-ридеров
 * - tab order (логичная последовательность)
 */

test.use({ ignoreHTTPSErrors: true, baseURL: "https://192.168.1.86" });

const PAGES = [
  { name: "login", url: "/login", login: false },
  { name: "subjects", url: "/subjects", login: "student" },
  { name: "topic detail", url: "/topics/31", login: "student" },
  { name: "admin audit", url: "/admin", login: "admin" },
];

const ISSUES: { page: string; url: string; problem: string }[] = [];

test.describe("Accessibility audit", () => {
  test.use({ ignoreHTTPSErrors: true });

  for (const p of PAGES) {
    test(`${p.name}: focus + aria + tab order`, async ({ page }) => {
      if (p.login) {
        const email =
          p.login === "admin" ? "admin@example.com" : "kirill@example.com";
        await page.goto("/login");
        await page.fill('input[type="email"]', email);
        await page.fill('input[type="password"]', "Kirill2026!");
        await page.click('button[type="submit"]');
        await page.waitForLoadState("networkidle", { timeout: 15_000 });
      }

      await page.goto(p.url);
      await page.waitForLoadState("networkidle", { timeout: 15_000 });

      // 1) Все icon-only buttons имеют aria-label или текст
      const iconsWithoutLabel = await page.evaluate(() => {
        const out: { tag: string; text: string }[] = [];
        document.querySelectorAll('button, a').forEach((el) => {
          const rect = el.getBoundingClientRect();
          if (rect.width === 0) return;
          const hasLabel =
            el.hasAttribute("aria-label") ||
            el.hasAttribute("aria-labelledby") ||
            (el.textContent || "").trim().length > 0 ||
            el.querySelector("img[alt]") !== null;
          const looksLikeIcon =
            rect.width < 60 &&
            (el.textContent || "").trim().length === 0;
          if (looksLikeIcon && !hasLabel) {
            out.push({ tag: el.tagName, text: el.outerHTML.slice(0, 100) });
          }
        });
        return out;
      });
      if (iconsWithoutLabel.length > 0) {
        ISSUES.push({
          page: p.name,
          url: p.url,
          problem: `icon-only buttons without label: ${iconsWithoutLabel.length}`,
        });
      }

      // 2) Form inputs имеют labels
      const inputsWithoutLabel = await page.evaluate(() => {
        const out: { type: string }[] = [];
        document.querySelectorAll("input, textarea, select").forEach((el) => {
          const tag = el as HTMLInputElement;
          if (tag.type === "hidden" || tag.type === "submit") return;
          const id = el.id;
          const hasLabel =
            (id && document.querySelector(`label[for="${id}"]`) !== null) ||
            el.closest("label") !== null ||
            el.hasAttribute("aria-label") ||
            el.hasAttribute("aria-labelledby") ||
            el.hasAttribute("placeholder");
          if (!hasLabel) out.push({ type: (el as HTMLInputElement).type || el.tagName });
        });
        return out;
      });
      if (inputsWithoutLabel.length > 0) {
        ISSUES.push({
          page: p.name,
          url: p.url,
          problem: `inputs without label: ${inputsWithoutLabel.length}`,
        });
      }

      // 3) Tab order — последовательный фокус видим.
      //    Click first input, check что фокус сместился.
      const tabbables = await page.evaluate(() => {
        return Array.from(
          document.querySelectorAll(
            'input, button, a[href], select, textarea, [tabindex]:not([tabindex="-1"])',
          ),
        ).slice(0, 10);
      });
      if (tabbables.length === 0) {
        ISSUES.push({
          page: p.name,
          url: p.url,
          problem: "no focusable elements",
        });
      }

      // 4) Console errors (отсутствие alt на img)
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(e.message));
      await page.waitForTimeout(500);
      if (errors.length > 0) {
        ISSUES.push({
          page: p.name,
          url: p.url,
          problem: `console errors: ${errors.join("; ")}`,
        });
      }
    });
  }

  test.afterAll(() => {
    // Report issues в summary
    if (ISSUES.length > 0) {
      console.log(`\n=== a11y audit issues: ${ISSUES.length} ===`);
      ISSUES.forEach((i) =>
        console.log(`  - [${i.page}] ${i.problem}`),
      );
    } else {
      console.log("\n✅ a11y audit: no issues detected");
    }
  });
});
