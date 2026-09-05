/**
 * Sprint 3.37: visual regression snapshots для 6 публичных страниц × 2 viewport.
 *
 * Покрывает: landing, login, register, forgot-password, link-parent, offline.
 * Авторизованные страницы (dashboard, /parents, /student) — НЕ покрыты,
 * требуют whitelist-creds (НЕ ТРОГАТЬ whitelist).
 *
 * Запуск:
 *   cd apps/frontend && npx playwright test e2e/snapshots-public.spec.ts
 *
 * При первом запуске создаёт baseline (`--update-snapshots`):
 *   npx playwright test e2e/snapshots-public.spec.ts --update-snapshots
 *
 * Снапшоты лежат в e2e/snapshots-public.spec.ts-snapshots/
 */

import { test, expect, type Page } from "@playwright/test";

const TARGETS = [
  { name: "landing", path: "/" },
  { name: "login", path: "/login" },
  { name: "register", path: "/register" },
  { name: "forgot-password", path: "/forgot-password" },
  { name: "link-parent", path: "/link-parent" },
  { name: "offline", path: "/offline" },
] as const;

// Disable CSS animations and transitions для стабильных скриншотов.
async function freezeAnimations(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `,
  });
}

for (const target of TARGETS) {
  test.describe(`Snapshot: ${target.name}`, () => {
    test(`desktop (1280x720)`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 720 });
      await page.goto(target.path, { waitUntil: "networkidle" });
      await freezeAnimations(page);
      await expect(page).toHaveScreenshot(`${target.name}-desktop.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02, // ≤2% diff tolerated (font rendering может варьировать)
      });
    });

    test(`mobile (375x667 — iPhone SE)`, async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(target.path, { waitUntil: "networkidle" });
      await freezeAnimations(page);
      await expect(page).toHaveScreenshot(`${target.name}-mobile.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  });
}
