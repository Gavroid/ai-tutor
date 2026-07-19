/**
 * Sprint 11.2 — accessibility audit (WCAG 2.1).
 *
 * Проверяет на 4 key pages:
 * - form inputs имеют associated labels (для screen reader)
 * - icon-only buttons имеют aria-label
 * - есть focusable elements (keyboard nav работает)
 * - нет console errors
 */
import { test, expect } from "@playwright/test";

test.use({ ignoreHTTPSErrors: true, baseURL: "https://192.168.1.86" });

const PAGES = [
  { name: "login", url: "/login", login: false },
  { name: "subjects", url: "/subjects", login: "student" },
  { name: "topic", url: "/topics/31", login: "student" },
  { name: "admin_audit", url: "/admin", login: "admin" },
];

for (const p of PAGES) {
  test(`a11y_${p.name}`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));

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

    // 1) Inputs without associated label — accessibility violation.
    const inputsNoLabel = await page.evaluate(() => {
      const out: { type: string }[] = [];
      const inputs = document.querySelectorAll("input, textarea, select");
      for (const el of Array.from(inputs)) {
        const tag = el as HTMLInputElement;
        if (tag.type === "hidden" || tag.type === "submit") continue;
        const id = tag.id;
        const hasLabel =
          (id && document.querySelector(`label[for="${id}"]`) !== null) ||
          tag.closest("label") !== null ||
          tag.hasAttribute("aria-label") ||
          tag.hasAttribute("aria-labelledby") ||
          tag.hasAttribute("placeholder");
        if (!hasLabel) out.push({ type: tag.type || tag.tagName });
      }
      return out;
    });

    // 2) Icon-only buttons without label.
    const iconsNoLabel = await page.evaluate(() => {
      const out: { tag: string }[] = [];
      const els = document.querySelectorAll("button, a[href]");
      for (const el of Array.from(els)) {
        const tag = el as HTMLElement;
        const rect = tag.getBoundingClientRect();
        if (rect.width === 0) continue;
        const hasLabel =
          tag.hasAttribute("aria-label") ||
          tag.hasAttribute("aria-labelledby") ||
          (tag.textContent || "").trim().length > 0;
        const looksLikeIcon =
          rect.width < 60 && (tag.textContent || "").trim().length === 0;
        if (looksLikeIcon && !hasLabel) out.push({ tag: tag.tagName });
      }
      return out;
    });

    // 3) Tab order — есть focusable elements.
    const tabbables = await page.evaluate(() => {
      return document.querySelectorAll(
        'input, button, a[href], select, textarea, [tabindex]:not([tabindex="-1"])',
      ).length;
    });

    expect(inputsNoLabel.length, `${p.name} inputs without label`).toBe(0);
    expect(iconsNoLabel.length, `${p.name} icon-only without label`).toBe(0);
    expect(tabbables, `${p.name} tabbable count`).toBeGreaterThan(0);
    expect(errors.length, `${p.name} console errors`).toBe(0);
  });
}
